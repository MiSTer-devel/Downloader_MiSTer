# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
import time
from abc import ABC, abstractmethod

from downloader.constants import file_MiSTer, file_MiSTer_new
from downloader.logger import SilentLogger
from downloader.other import calculate_url, NoArgumentsToComputeUrlError
from downloader.target_path_repository import TargetPathRepository


class FileDownloaderFactory(ABC):
    @abstractmethod
    def create(self, config, parallel_update, silent=False, hash_check=True):
        """Created a Parallel or Serial File Downloader"""


def make_file_downloader_factory(file_system_factory, local_repository, logger):
    return _FileDownloaderFactoryImpl(file_system_factory, local_repository, logger)


class _FileDownloaderFactoryImpl(FileDownloaderFactory):
    def __init__(self, file_system_factory, local_repository, logger):
        self._file_system_factory = file_system_factory
        self._local_repository = local_repository
        self._logger = logger

    def create(self, config, parallel_update, silent=False, hash_check=True):
        logger = SilentLogger(self._logger) if silent else self._logger
        file_system = self._file_system_factory.create_for_config(config)
        if parallel_update:
            return _CurlCustomParallelDownloader(config, file_system, self._local_repository, logger, hash_check, TargetPathRepository(config, file_system))
        else:
            return _CurlSerialDownloader(config, file_system, self._local_repository, logger, hash_check, TargetPathRepository(config, file_system))


class FileDownloader(ABC):
    @abstractmethod
    def queue_file(self, file_description, file_path):
        """queues a file for downloading it later"""

    @abstractmethod
    def set_base_files_url(self, base_files_url):
        """sets the base_files_url from a database"""

    @abstractmethod
    def mark_unpacked_zip(self, zip_id, base_zips_url):
        """indicates that a zip is being used, useful for reporting"""

    @abstractmethod
    def download_files(self,  first_run):
        """download all the queued files"""

    @abstractmethod
    def errors(self):
        """all files with errors"""

    @abstractmethod
    def correctly_downloaded_files(self):
        """all correctly downloaded files"""

    @abstractmethod
    def needs_reboot(self):
        """returns true if a file that needs reboot has been downloaded"""


class CurlDownloaderAbstract(FileDownloader):
    def __init__(self, config, file_system, local_repository, logger, hash_check, temp_files_registry):
        self._config = config
        self._file_system = file_system
        self._logger = logger
        self._local_repository = local_repository
        self._hash_check = hash_check
        self._temp_files_registry = temp_files_registry
        self._curl_list = {}
        self._errors = _DownloadErrors(logger)
        self._http_oks = _HttpOks()
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

        if self._file_system.is_file(file_MiSTer_new):
            self._logger.print()
            self._logger.print('Copying new MiSTer binary:')
            if self._file_system.is_file(file_MiSTer):
                self._file_system.move(file_MiSTer, self._local_repository.old_mister_path)
            self._file_system.move(file_MiSTer_new, file_MiSTer)

            if self._file_system.is_file(file_MiSTer):
                self._logger.print('New MiSTer binary copied.')
            else:
                # This error message should never happen.
                # If it happens it would be an unexpected case where file_system is not moving files correctly
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
                self._file_system.add_system_path(path)
                if path == file_MiSTer:
                    self._file_system.add_system_path(file_MiSTer_new)

            if self._hash_check and self._file_system.is_file(path):
                path_hash = self._file_system.hash(path)
                if path_hash == self._curl_list[path]['hash']:
                    if 'zip_id' in self._curl_list[path] and self._curl_list[path]['zip_id'] in self._unpacked_zips:
                        self._logger.print('Unpacked: %s' % path)
                    else:
                        self._logger.print('No changes: %s' % path)
                    self._correct_downloads.append(path)
                    continue
                else:
                    self._logger.debug('%s: %s != %s' % (path, self._curl_list[path]['hash'], path_hash))

            if first_run:
                if 'delete' in self._curl_list[path]:
                    for _ in self._curl_list[path]['delete']:
                        self._file_system.delete_previous(path)
                        break
                elif 'delete_previous' in self._curl_list[path] and self._curl_list[path]['delete_previous']:
                    self._file_system.delete_previous(path)

            self._download(path, self._curl_list[path])

        self._wait()
        self._check_hashes()

        for retry in range(self._config['downloader_retries']):

            if self._errors.none():
                return

            for path in self._errors.consume():
                self._download(path, self._curl_list[path])

            self._wait()
            self._check_hashes()

    def _check_hashes(self):
        if self._http_oks.none():
            return

        self._logger.print()
        self._logger.print('Checking hashes...')

        for path in self._http_oks.consume():
            if not self._file_system.is_file(self._temp_files_registry.access_target(path)):
                self._errors.add_debug_report(path, 'Missing %s' % path)
                continue

            path_hash = self._file_system.hash(self._temp_files_registry.access_target(path))
            if self._hash_check and path_hash != self._curl_list[path]['hash']:
                self._errors.add_debug_report(path, 'Bad hash on %s (%s != %s)' % (path, self._curl_list[path]['hash'], path_hash))
                self._temp_files_registry.clean_target(path)
                continue

            self._temp_files_registry.finish_target(path)
            self._logger.print('+', end='', flush=True)
            self._correct_downloads.append(path)
            if self._curl_list[path].get('reboot', False):
                self._needs_reboot = True

        self._logger.print()

    def _download(self, path, description):
        self._logger.print(path)
        self._file_system.make_dirs_parent(path)

        if 'url' not in description:
            description['url'] = calculate_url(self._base_files_url, path)

        target_path = self._temp_files_registry.create_target(path, description)

        self._run(description, self._command(target_path, description['url']), path)

    def _command(self, target_path, url):
        return 'curl %s --show-error --fail --location -o "%s" "%s"' % (self._config['curl_ssl'], target_path, url)

    def errors(self):
        return self._errors.list()

    def correctly_downloaded_files(self):
        return self._correct_downloads

    def needs_reboot(self):
        return self._needs_reboot

    @abstractmethod
    def _wait(self):
        """"waits until all downloads are completed"""

    @abstractmethod
    def _run(self, description, command, path):
        """"starts the downloading process"""


class _CurlCustomParallelDownloader(CurlDownloaderAbstract):
    def __init__(self, config, file_system, local_repository, logger, hash_check, temp_file_registry):
        super().__init__(config, file_system, local_repository, logger, hash_check, temp_file_registry)
        self._processes = []
        self._files = []
        self._acc_size = 0

    def _run(self, description, command, file):
        self._acc_size = self._acc_size + description['size']

        result = subprocess.Popen(shlex.split(command), shell=False, stderr=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL)

        self._processes.append(result)
        self._files.append(file)

        more_accumulated_size_than_limit = self._acc_size > (1000 * 1000 * self._config['downloader_size_mb_limit'])
        more_processes_than_limit = len(self._processes) > self._config['downloader_process_limit']

        if more_accumulated_size_than_limit or more_processes_than_limit:
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
                        self._http_oks.add(self._files[i])
                    else:
                        self._errors.add_debug_report(self._files[i], 'Bad http code! %s: %s' % (result, self._files[i]))
            end = time.time()
            if (end - start) > self._config['downloader_timeout']:
                for i, p in enumerate(self._processes):
                    if p is None:
                        continue
                    self._errors.add_debug_report(self._files[i], 'Timeout! %s' % self._files[i])
                break

            time.sleep(1)
            if not some_completed:
                self._logger.print('*', end='', flush=True)

        self._logger.print(flush=True)
        self._processes = []
        self._files = []
        self._acc_size = 0


class _CurlSerialDownloader(CurlDownloaderAbstract):
    def __init__(self, config, file_system, local_repository, logger, hash_check, temp_file_registry):
        super().__init__(config, file_system, local_repository, logger, hash_check, temp_file_registry)

    def _run(self, description, command, file):
        result = subprocess.run(shlex.split(command), shell=False, stderr=subprocess.STDOUT)
        if result.returncode == 0:
            self._http_oks.add(file)
        else:
            self._errors.add_print_report(file, 'Bad http code! %s: %s' % (result.returncode, file))

        self._logger.print()

    def _wait(self):
        pass


class _DownloadErrors:
    def __init__(self, logger):
        self._logger = logger
        self._errors = []

    def add_debug_report(self, path, message):
        self._logger.print('~', end='', flush=True)
        self._logger.debug(message, flush=True)
        self._errors.append(path)

    def add_print_report(self, path, message):
        self._logger.print(message, flush=True)
        self._errors.append(path)

    def none(self):
        return len(self._errors) == 0

    def consume(self):
        errors = self._errors
        self._errors = []
        return errors

    def list(self):
        return self._errors


class _HttpOks:
    def __init__(self):
        self._oks = []

    def add(self, path):
        self._oks.append(path)

    def consume(self):
        oks = self._oks
        self._oks = []
        return oks

    def none(self):
        return len(self._oks) == 0
