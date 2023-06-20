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
import sys
import socket
import ssl
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
from shutil import copyfileobj
from typing import Tuple, Union, Dict, Any, Optional
from urllib.error import URLError
from http.client import HTTPException

from downloader.constants import K_DOWNLOADER_RETRIES, K_DOWNLOADER_TIMEOUT, K_CURL_SSL, FILE_MiSTer_new, FILE_MiSTer, \
    FILE_MiSTer_old, K_DOWNLOADER_THREADS_LIMIT, K_DEBUG
from downloader.file_system import FolderCreationError
from downloader.http_gateway import HttpGateway, HttpGatewayException
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
    def failed_folders(self):
        """all folders that could not be created"""

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
    def create_low_level_file_downloader(self, high_level) -> LowLevelFileDownloader:
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
        self._failed_folders = []

    def failed_folders(self):
        return self._failed_folders

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
        self._fetch_whole_queue(low_level)
        self._check_downloaded_files(low_level.downloaded_files())
        return low_level.network_errors()

    def _fetch_whole_queue(self, low_level: LowLevelFileDownloader) -> None:
        files_to_download = []
        skip_files = []
        for file_path, file_description in self._queued_files.items():
            try:
                target_path = self._prepare_target_path_in_whole_queue(file_path, file_description)
            except FolderCreationError as folder_path:
                self._logger.print('ERROR: Folder for file "%s" could not be created, skipping.' % file_path)
                self._logger.debug(file_path)
                self._failed_folders.append(folder_path)
                continue

            if target_path is None:
                skip_files.append(file_path)
            else:
                files_to_download.append((file_path, target_path))
                self._run_files.append(file_path)

        for file_path in skip_files:
            self._correct_files.append(file_path)
            self._queued_files.pop(file_path)

        low_level.fetch(files_to_download, self._queued_files)

    def _prepare_target_path_in_whole_queue(self, file_path: str, file_description: Dict[str, Any]) -> Optional[str]:
        if self._hash_check and self._file_system.is_file(file_path):
            path_hash = self._file_system.hash(file_path)
            if path_hash == file_description['hash']:
                if 'zip_id' in file_description and file_description['zip_id'] in self._unpacked_zips:
                    self._logger.print('Unpacked: %s' % file_path)
                else:
                    self._logger.print('No changes: %s' % file_path)  # @TODO This scenario might be redundant now, since it's also checked in the Online Importer
                return None
            else:
                self._logger.debug('%s: %s != %s' % (file_path, file_description['hash'], path_hash))

        if 'url' not in file_description:
            file_description['url'] = calculate_url(self._base_files_url, file_path)

        self._file_system.make_dirs_parent(file_path)
        target_path = self._target_path_repository.create_target(file_path, file_description)
        return self._file_system.download_target_path(target_path)

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

    def create_low_level_file_downloader(self, download_validator) -> LowLevelFileDownloader:
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
        self._newline_pending = False

    def fetch(self, files_to_download, descriptions):
        job_queue = queue.Queue()
        notify_queue = queue.Queue()
        for path, target in files_to_download:
            job_queue.put((descriptions[path]['url'], path, target), False)

        http_logger = self._logger if self._config[K_DEBUG] else None
        with HttpGateway(self._context, self._config[K_DOWNLOADER_TIMEOUT], logger=http_logger) as http_gateway:
            with ThreadPoolExecutor(max_workers=self._threads_limit) as executor:
                futures = [executor.submit(_thread_worker, http_gateway, job_queue, notify_queue) for _ in files_to_download]

                remaining_notifications = len(files_to_download) * 2

                while remaining_notifications > 0:
                    remaining_notifications -= self._read_notifications(descriptions, notify_queue, True)
                    self._waiter.sleep(1)

                job_queue.join()
                wait(futures)

        self._read_notifications(descriptions, notify_queue, False)
        self._logger.print()

    def _read_notifications(self, descriptions, notify_queue, in_progress):
        new_files = False
        read_notifications = 0
        while not notify_queue.empty():
            state, path = notify_queue.get(False)
            notify_queue.task_done()

            if state == 0:
                if self._newline_pending:
                    self._newline_pending = False
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

        self._newline_pending = in_progress
        self._pending_notifications.clear()
        return read_notifications

    def network_errors(self):
        return self._network_errors.list()

    def downloaded_files(self):
        return self._downloaded_files


def _thread_worker(http_gateway: HttpGateway, job_queue: queue.Queue, notify_queue: queue.Queue) -> None:
    while not job_queue.empty():
        url, path, target = job_queue.get(False)

        notify_queue.put((0, path), False)
        try:
            with http_gateway.open(url) as (final_url, in_stream), open(target, 'wb') as out_file:
                url = final_url
                if in_stream.status == 200:
                    copyfileobj(in_stream, out_file)
                    notify_queue.put((1, path), False)
                else:
                    notify_queue.put((2, (path, 'Bad http status! %s: %s' % (path, in_stream.status))), False)

        except socket.gaierror as e:
            notify_queue.put((2, (path, 'Socket Address Error! %s: %s' % (url, str(e)))), False)
        except URLError as e:
            notify_queue.put((2, (path, 'URL Error! %s: %s' % (url, e.reason))), False)
        except HttpGatewayException as e:
            notify_queue.put((2, (path, 'Http Gateway Error %s! %s: %s' % (type(e).__name__, url, str(e)))), False)
        except HTTPException as e:
            notify_queue.put((2, (path, 'HTTP Error %s! %s: %s' % (type(e).__name__, url, str(e)))), False)
        except ConnectionResetError as e:
            notify_queue.put((2, (path, 'Connection reset error! %s: %s' % (url, str(e)))), False)
        except OSError as e:
            notify_queue.put((2, (path, 'OS Error! %s: %s %s' % (url, e.errno, str(e)))), False)
        except Exception as e:
            notify_queue.put((2, (path, 'Exception during download! %s: %s' % (url, str(e)))), False)

        job_queue.task_done()


class _DownloadErrors:
    def __init__(self, logger):
        self._logger = logger
        self._errors = []

    def add_debug_report(self, path, message):
        self._logger.print('~', end='', flush=True)
        self._logger.debug(message, flush=True)
        self._errors.append(path)

    def list(self):
        return self._errors
