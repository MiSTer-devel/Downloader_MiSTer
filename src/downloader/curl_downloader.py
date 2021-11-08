# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# You can download the latest version of this tool from:
# https://github.com/MiSTer-devel/Downloader_MiSTer

import shlex
import subprocess
import sys
from urllib.parse import quote, urlparse
import urllib.request
import time


def make_downloader_factory(file_service, local_repository, logger):
    return lambda config: CurlCustomParallelDownloader(config, file_service, local_repository, logger) if config[
        'parallel_update'] else CurlSerialDownloader(config, file_service, local_repository, logger)


class CurlCommonDownloader:
    def __init__(self, config, file_service, local_repository, logger):
        self._config = config
        self._file_service = file_service
        self._logger = logger
        self._local_repository = local_repository
        self._curl_list = {}
        self._errors = []
        self._http_oks = []
        self._correct_downloads = []
        self._needs_reboot = False
        self._base_files_url = None
        self._unpacked_zips = dict()

    def queue_file(self, file_description, file_path):
        self._curl_list[file_path] = file_description

    def set_base_files_url(self, base_files_url):
        self._base_files_url = base_files_url

    def mark_unpacked_zip(self, zip_id, base_zips_url):
        self._unpacked_zips[zip_id] = base_zips_url

    def download_files(self, first_run):
        self._download_files_internal(first_run)

        if self._file_service.is_file('MiSTer.new'):
            self._logger.print()
            self._logger.print('Copying new MiSTer binary:')
            if self._file_service.is_file('MiSTer'):
                self._file_service.move('MiSTer', self._local_repository.old_mister_path)
            self._file_service.move('MiSTer.new', 'MiSTer')

            if self._file_service.is_file('MiSTer'):
                self._logger.print('New MiSTer binary copied.')
            else:
                # This error message should never happen.
                # If it happens it would be an unexpected case where file_service is not moving files correctly
                self._logger.print('CRITICAL ERROR!!! Could not restore the MiSTer binary!')
                self._logger.print('Please manually rename the file MiSTer.new as MiSTer')
                self._logger.print('Your system won\'nt be able to boot until you do so!')
                sys.exit(1)

    def _download_files_internal(self, first_run):
        if len(self._curl_list) == 0:
            self._logger.print("Nothing new to download from given sources.")
            return

        self._logger.print("Downloading %d files:" % len(self._curl_list))

        for path in sorted(self._curl_list):
            if 'path' in self._curl_list[path] and self._curl_list[path]['path'] == 'system':
                self._file_service.add_system_path(path)

            if self._file_service.is_file(path):
                path_hash = self._file_service.hash(path)
                if path_hash == self._curl_list[path]['hash']:
                    if 'zip_id' in self._curl_list[path] and self._curl_list[path]['zip_id'] in self._unpacked_zips:
                        self._logger.print('Unpacked: %s' % path)
                    else:
                        self._logger.print('No changes: %s' % path)
                    self._correct_downloads.append(path)
                    continue
                else:
                    self._logger.debug('%s: %s != %s' % (path, self._curl_list[path]['hash'], path_hash))

            if first_run and 'delete' in self._curl_list[path]:
                for delete in self._curl_list[path]['delete']:
                    self._file_service.clean_expression(delete)

            self._download(path, self._curl_list[path])

        self._wait()
        self._check_hashes()

        for retry in range(self._config['downloader_retries']):

            if len(self._errors) == 0:
                return

            missing = self._errors
            self._errors = []

            for path in missing:
                self._download(path, self._curl_list[path])

            self._wait()
            self._check_hashes()

    def _check_hashes(self):
        if len(self._http_oks) > 0:
            self._logger.print()
            self._logger.print('Checking hashes...')

            for path in self._http_oks:
                if not self._file_service.is_file(path if path != 'MiSTer' else 'MiSTer.new'):
                    self._logger.print('~', end='', flush=True)
                    self._logger.debug('Missing %s' % path)
                    self._errors.append(path)
                    continue

                path_hash = self._file_service.hash(path if path != 'MiSTer' else 'MiSTer.new')
                if path_hash != self._curl_list[path]['hash']:
                    self._logger.print('~', end='', flush=True)
                    self._logger.debug(
                        'Bad hash on %s (%s != %s)' % (path, self._curl_list[path]['hash'], path_hash))
                    self._errors.append(path)
                    continue

                self._logger.print('+', end='', flush=True)
                self._correct_downloads.append(path)
                if self._curl_list[path].get('reboot', False):
                    self._needs_reboot = True

            self._logger.print()

        self._http_oks = []

    def _download(self, path, description):
        self._logger.print(path)
        self._file_service.makedirs_parent(path)

        if 'url' not in description:
            description['url'] = self._url_from_path(path)

        url_domain = urlparse(description['url']).netloc
        url_parts = description['url'].split(url_domain)

        target_path = self._file_service.curl_target_path(path if path != 'MiSTer' else 'MiSTer.new')
        url = url_parts[0] + url_domain + urllib.parse.quote(url_parts[1])

        self._run(description, self._command(target_path, url), path)

    def _command(self, target_path, url):
        return 'curl %s --show-error --fail --location -o "%s" "%s"' % (self._config['curl_ssl'], target_path, url)

    def _url_from_path(self, path):
        if self._base_files_url is None:
            raise Exception('Trying to process %s, but no base_files_url filed has been provided to calculate the url.' % path)
        return self._base_files_url + path

    def errors(self):
        return self._errors

    def correctly_downloaded_files(self):
        return self._correct_downloads

    def needs_reboot(self):
        return self._needs_reboot

    def _wait(self):
        raise NotImplementedError()

    def _run(self, description, command, path):
        raise NotImplementedError()


class CurlCustomParallelDownloader(CurlCommonDownloader):
    def __init__(self, config, file_service, local_repository, logger):
        super().__init__(config, file_service, local_repository, logger)
        self._processes = []
        self._files = []
        self._acc_size = 0

    def _run(self, description, command, file):
        self._acc_size = self._acc_size + description['size']

        result = subprocess.Popen(shlex.split(command), shell=False, stderr=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL)

        self._processes.append(result)
        self._files.append(file)

        if self._acc_size > (1000 * 1000 * self._config['downloader_size_mb_limit']) or len(self._processes) > \
                self._config['downloader_process_limit']:
            self._wait()

    def _wait(self):
        count = 0
        start = time.time()
        while count < len(self._processes):
            some_completed = False
            for i, p in enumerate(self._processes):
                if p is None:
                    continue
                result = p.poll()
                if result is not None:
                    self._processes[i] = None
                    some_completed = True
                    count = count + 1
                    start = time.time()
                    self._logger.print('.', end='', flush=True)
                    if result == 0:
                        self._http_oks.append(self._files[i])
                    else:
                        self._logger.print('~', end='', flush=True)
                        self._logger.debug('Bad http code! %s: %s' % (result, self._files[i]), flush=True)
                        self._errors.append(self._files[i])
            end = time.time()
            if (end - start) > self._config['downloader_timeout']:
                for i, p in enumerate(self._processes):
                    if p is None:
                        continue
                    self._logger.print('~', end='', flush=True)
                    self._logger.debug('Timeout! %s' % self._files[i], flush=True)
                    self._errors.append(self._files[i])
                break

            time.sleep(1)
            if not some_completed:
                self._logger.print('*', end='', flush=True)

        self._logger.print(flush=True)
        self._processes = []
        self._files = []
        self._acc_size = 0


class CurlSerialDownloader(CurlCommonDownloader):
    def __init__(self, config, file_service, local_repository, logger):
        super().__init__(config, file_service, local_repository, logger)

    def _run(self, description, command, file):
        result = subprocess.run(shlex.split(command), shell=False, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            self._http_oks.append(file)
        else:
            self._logger.print('Bad http code! %s: %s' % (result.returncode, file), flush=True)
            self._errors.append(file)

        self._logger.print()

    def _wait(self):
        pass
