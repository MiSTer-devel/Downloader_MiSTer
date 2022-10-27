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
import queue
import shlex
import ssl
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from shutil import copyfileobj
from threading import Thread
from typing import Tuple, Union
from urllib.error import URLError
from urllib.request import urlopen

from downloader.constants import K_DOWNLOADER_RETRIES, K_DOWNLOADER_SIZE_MB_LIMIT, \
    K_DOWNLOADER_PROCESS_LIMIT, K_DOWNLOADER_TIMEOUT, K_CURL_SSL, K_DEBUG, FILE_MiSTer_new, FILE_MiSTer, \
    FILE_MiSTer_old, K_DOWNLOADER_OLD_IMPLEMENTATION, K_DOWNLOADER_THREADS_LIMIT
from downloader.logger import DebugOnlyLoggerDecorator
from downloader.other import calculate_url
from downloader.target_path_repository import TargetPathRepository


class FileDownloaderFactory(ABC):
    @abstractmethod
    def create(self, config, parallel_update, silent=False, hash_check=True):
        """Created a Parallel or Serial File Downloader"""


def make_file_downloader_factory(file_system_factory, local_repository, waiter, logger):
    return _FileDownloaderFactoryImpl(file_system_factory, local_repository, waiter, logger)


class _FileDownloaderFactoryImpl(FileDownloaderFactory):
    def __init__(self, file_system_factory, local_repository, waiter, logger):
        self._file_system_factory = file_system_factory
        self._local_repository = local_repository
        self._waiter = waiter
        self._logger = logger

    def create(self, config, parallel_update, silent=False, hash_check=True):
        logger = DebugOnlyLoggerDecorator(self._logger) if silent else self._logger
        file_system = self._file_system_factory.create_for_config(config)
        target_path_repository = TargetPathRepository(config, file_system)
        if config[K_DOWNLOADER_OLD_IMPLEMENTATION]:
            self._logger.print('Using old downloader implementation...')
            if parallel_update:
                return _CurlCustomParallelDownloader(config, file_system, self._local_repository, logger, hash_check, target_path_repository)
            else:
                return _CurlSerialDownloader(config, file_system, self._local_repository, logger, hash_check, target_path_repository)
        else:
            thread_limit = config[K_DOWNLOADER_THREADS_LIMIT] if parallel_update else 1
            low_level_factory = _LowLevelMultiThreadingFileDownloaderFactory(thread_limit, config, self._waiter, logger)
            return HighLevelFileDownloader(hash_check, config, file_system, target_path_repository, low_level_factory, logger)


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


class LowLevelFileDownloader(ABC):
    def fetch(self, files_to_download, paths):
        """"files_to_download is a dictionary with file_path as keys and file_description as values"""

    def network_errors(self):
        """returns errors that happened during download_files"""

    def downloaded_files(self):
        """returns files downloaded during download_files"""


class LowLevelFileDownloaderFactory(ABC):
    def create_low_level_file_downloader(self, high_level):
        """"returns instance of LowLevelFileDownloader"""


class DownloadValidator(ABC):
    def validate_download(self, file_path: str, file_hash: str) -> Tuple[int, Union[str, Tuple[str, str]]]:
        """Validates that the downloaded file is correctly installed and moves it if necessary. Returned int is 1 if validation was correct."""


class HighLevelFileDownloader(FileDownloader, DownloadValidator):
    def __init__(self, hash_check, config, file_system, target_path_repository, low_level_file_downloader_factory, logger):
        self._hash_check = hash_check
        self._file_system = file_system
        self._target_path_repository = target_path_repository
        self._config = config
        self._low_level_file_downloader_factory = low_level_file_downloader_factory
        self._logger = logger
        self._run_files = []
        self._queued_files = {}
        self._base_files_url = None
        self._unpacked_zips = {}
        self._needs_reboot = False
        self._errors = []
        self._correct_files = []

    def queue_file(self, file_description, file_path):
        self._queued_files[file_path] = file_description

    def set_base_files_url(self, base_files_url):
        self._base_files_url = base_files_url

    def mark_unpacked_zip(self, zip_id, base_zips_url):
        self._unpacked_zips[zip_id] = base_zips_url

    def download_files(self, _):
        for _ in range(self._config[K_DOWNLOADER_RETRIES] + 1):
            self._errors = self._download_try()
            if len(self._errors):
                continue

            break

        if self._file_system.is_file(FILE_MiSTer_new):
            self._logger.print('')
            self._logger.print('Copying new MiSTer binary:')
            if self._file_system.is_file(FILE_MiSTer):
                self._file_system.move(FILE_MiSTer, FILE_MiSTer_old)
            self._file_system.move(FILE_MiSTer_new, FILE_MiSTer)

            if self._file_system.is_file(FILE_MiSTer):
                self._logger.print('New MiSTer binary copied.')
            else:
                # This error message should never happen.
                # If it happens it would be an unexpected case where file_system is not moving files correctly
                self._logger.print('CRITICAL ERROR!!! Could not restore the MiSTer binary!')
                self._logger.print('Please manually rename the file MiSTer.new as MiSTer')
                self._logger.print('Your system won\'nt be able to boot until you do so!')
                sys.exit(1)

    def _download_try(self):
        if len(self._queued_files) == 0:
            self._logger.print("Nothing new to download from given sources.")
            return []

        self._logger.print("Downloading %d files:" % len(self._queued_files))

        low_level = self._low_level_file_downloader_factory.create_low_level_file_downloader(self)

        files_to_download = []
        skip_files = []
        for file_path, file_description in self._queued_files.items():
            if self._hash_check and self._file_system.is_file(file_path):
                path_hash = self._file_system.hash(file_path)
                if path_hash == file_description['hash']:
                    if 'zip_id' in file_description and file_description['zip_id'] in self._unpacked_zips:
                        self._logger.print('Unpacked: %s' % file_path)
                    else:
                        self._logger.print('No changes: %s' % file_path)  # @TODO This scenario might be redundant now, since it's also checked in the Online Importer
                    skip_files.append(file_path)
                    continue
                else:
                    self._logger.debug('%s: %s != %s' % (file_path, file_description['hash'], path_hash))

            if 'url' not in file_description:
                file_description['url'] = calculate_url(self._base_files_url, file_path)

            self._file_system.make_dirs_parent(file_path)
            target_path = self._target_path_repository.create_target(file_path, file_description)
            files_to_download.append((file_path, self._file_system.download_target_path(target_path)))
            self._run_files.append(file_path)

        for file_path in skip_files:
            self._correct_files.append(file_path)
            self._queued_files.pop(file_path)

        low_level.fetch(files_to_download, self._queued_files)

        self._check_downloaded_files(low_level.downloaded_files())

        return low_level.network_errors()

    def validate_download(self, file_path: str, file_hash: str) -> Tuple[int, Union[str, Tuple[str, str]]]:
        target_path = self._target_path_repository.access_target(file_path)
        if not self._file_system.is_file(target_path):
            return 2, (file_path, 'Missing %s' % file_path)

        path_hash = self._file_system.hash(target_path)
        if self._hash_check and path_hash != file_hash:
            self._target_path_repository.clean_target(file_path)
            return 2, (file_path, 'Bad hash on %s (%s != %s)' % (file_path, file_hash, path_hash))

        self._target_path_repository.finish_target(file_path)
        self._logger.debug('+', end='', flush=True)

        return 1, file_path

    def _check_downloaded_files(self, files):
        for path in files:
            self._correct_files.append(path)
            if self._queued_files[path].get('reboot', False):
                self._needs_reboot = True

            self._queued_files.pop(path)

    def errors(self):
        return self._errors

    def correctly_downloaded_files(self):
        return self._correct_files

    def needs_reboot(self):
        return self._needs_reboot

    def run_files(self):
        return self._run_files


def context_from_curl_ssl(curl_ssl):
    context = ssl.create_default_context()

    if curl_ssl.startswith('--cacert '):
        cacert_file = curl_ssl[len('--cacert '):]
        context.load_verify_locations(cacert_file)
    elif curl_ssl == '--insecure':
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    return context


class _LowLevelMultiThreadingFileDownloaderFactory(LowLevelFileDownloaderFactory):
    def __init__(self, threads_limit, config, waiter, logger):
        self._threads_limit = threads_limit
        self._config = config
        self._waiter = waiter
        self._logger = logger

    def create_low_level_file_downloader(self, download_validator):
        return _LowLevelMultiThreadingFileDownloader(self._threads_limit, self._config, context_from_curl_ssl(self._config[K_CURL_SSL]), self._waiter, self._logger, download_validator)


class _LowLevelMultiThreadingFileDownloader(LowLevelFileDownloader):
    def __init__(self, threads_limit, config, context, waiter, logger, download_validator):
        self._threads_limit = threads_limit
        self._config = config
        self._context = context
        self._waiter = waiter
        self._logger = logger
        self._download_validator = download_validator
        self._network_errors = _DownloadErrors(self._logger)
        self._downloaded_files = []
        self._pending_notifications = []
        self._endl_pending = False

    def fetch(self, files_to_download, descriptions):
        job_queue = queue.Queue()
        notify_queue = queue.Queue()
        for path, target in files_to_download:
            job_queue.put((descriptions[path]['url'], path, target), False)

        threads = [Thread(target=self._thread_worker, args=(job_queue, notify_queue)) for _ in range(min(self._threads_limit, len(files_to_download)))]
        for thread in threads:
            thread.start()

        remaining_notifications = len(files_to_download) * 2

        while remaining_notifications > 0:
            remaining_notifications -= self._read_notifications(descriptions, notify_queue, True)
            self._waiter.sleep(1)

        job_queue.join()

        for thread in threads:
            thread.join()

        self._read_notifications(descriptions, notify_queue, False)
        self._logger.print()

    def _read_notifications(self, descriptions, notify_queue, in_progress):
        new_files = False
        read_notifications = 0
        while not notify_queue.empty():
            state, path = notify_queue.get(False)
            notify_queue.task_done()

            if state == 0:
                if self._endl_pending:
                    self._endl_pending = False
                    self._logger.print()
                self._logger.print(path, flush=True)

                new_files = True
            elif state == 1:
                self._pending_notifications.append(self._download_validator.validate_download(path, descriptions[path]['hash']))
            else:
                self._pending_notifications.append((state, path))

            read_notifications += 1

        if new_files:
            return read_notifications

        if len(self._pending_notifications) > 0:
            for state, pack in self._pending_notifications:
                if state == 1:
                    path = pack
                    self._downloaded_files.append(path)
                    self._logger.print('.', end='', flush=True)
                else:
                    path, message = pack
                    self._network_errors.add_debug_report(path, message)
                    self._logger.print('~', end='', flush=True)

        elif in_progress:
            self._logger.print('*', end='', flush=True)

        self._endl_pending = in_progress
        self._pending_notifications.clear()
        return read_notifications

    def network_errors(self):
        return self._network_errors.list()

    def downloaded_files(self):
        return self._downloaded_files

    def _thread_worker(self, job_queue, notify_queue):
        while not job_queue.empty():
            url, path, target = job_queue.get(False)

            notify_queue.put((0, path), False)
            try:
                with urlopen(url, timeout=self._config[K_DOWNLOADER_TIMEOUT], context=self._context) as in_stream, open(target, 'wb') as out_file:
                    if in_stream.status == 200:
                        copyfileobj(in_stream, out_file)
                        notify_queue.put((1, path), False)
                    else:
                        notify_queue.put((2, (path, 'Bad http status! %s: %s' % (path, in_stream.status))), False)

            except URLError as e:
                notify_queue.put((2, (path, 'HTTP error! %s: %s' % (path, e.reason))), False)
            except ConnectionResetError as e:
                notify_queue.put((2, (path, 'Connection reset error! %s: %s' % (path, str(e)))), False)
            except Exception as e:
                notify_queue.put((2, (path, 'Exception during download! %s: %s' % (path, str(e)))), False)

            job_queue.task_done()


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

        if self._file_system.is_file(FILE_MiSTer_new):
            self._logger.print()
            self._logger.print('Copying new MiSTer binary:')
            if self._file_system.is_file(FILE_MiSTer):
                self._file_system.move(FILE_MiSTer, FILE_MiSTer_old)
            self._file_system.move(FILE_MiSTer_new, FILE_MiSTer)

            if self._file_system.is_file(FILE_MiSTer):
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
            description = self._curl_list[path]
            if self._hash_check and self._file_system.is_file(path):
                path_hash = self._file_system.hash(path)
                if path_hash == description['hash']:
                    if 'zip_id' in description and description['zip_id'] in self._unpacked_zips:
                        self._logger.print('Unpacked: %s' % path)
                    else:
                        self._logger.print('No changes: %s' % path)  # @TODO This scenario might be redundant now, since it's also checked in the Online Importer
                    self._correct_downloads.append(path)
                    continue
                else:
                    self._logger.debug('%s: %s != %s' % (path, description['hash'], path_hash))

            if first_run:
                if 'delete' in description:
                    for _ in description['delete']:  # @TODO This is Deprecated
                        self._file_system.delete_previous(path)
                        break
                elif 'delete_previous' in description and description['delete_previous']:
                    self._file_system.delete_previous(path)

            self._download(path, description)

        self._wait()
        self._check_hashes()

        for retry in range(self._config[K_DOWNLOADER_RETRIES]):

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
        if 'zip_path' in description:
            raise FileDownloaderError('zip_path is not a valid field for the file "%s", please contain the DB maintainer' % path)

        self._logger.print(path)
        self._file_system.make_dirs_parent(path)

        if 'url' not in description:
            description['url'] = calculate_url(self._base_files_url, path)

        target_path = self._temp_files_registry.create_target(path, description)

        if self._config[K_DEBUG] and target_path.startswith('/tmp/') and not description['url'].startswith('http'):
            self._file_system.copy(description['url'], target_path)
            self._run(description, 'echo > /dev/null', path)
            return

        self._run(description, self._command(target_path, description['url']), path)

    def _command(self, target_path, url):
        return 'curl %s --show-error --fail --location -o "%s" "%s"' % (self._config[K_CURL_SSL], target_path, url)

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

        more_accumulated_size_than_limit = self._acc_size > (1000 * 1000 * self._config[K_DOWNLOADER_SIZE_MB_LIMIT])
        more_processes_than_limit = len(self._processes) > self._config[K_DOWNLOADER_PROCESS_LIMIT]

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
            if (end - start) > self._config[K_DOWNLOADER_TIMEOUT]:
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


class FileDownloaderError(Exception):
    pass
