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

import sys
import ssl
from typing import Dict, Any

from downloader.constants import FILE_MiSTer_new, FILE_MiSTer, FILE_MiSTer_old
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FolderCreationError
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobSystem
from downloader.jobs.db_header_job import DbHeaderJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorkerContext, make_downloader_worker_context
from downloader.jobs.workers_factory import DownloaderWorkersFactory
from downloader.logger import DebugOnlyLoggerDecorator
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.target_path_repository import TargetPathRepository


class FileDownloaderFactory:
    def __init__(self, file_system_factory, waiter, logger, job_system, file_download_reporter, http_gateway, free_space_reservation: FreeSpaceReservation, external_drives_repository: ExternalDrivesRepository):
        self._file_system_factory = file_system_factory
        self._waiter = waiter
        self._logger = logger
        self._job_system = job_system
        self._file_download_reporter = file_download_reporter
        self._http_gateway = http_gateway
        self._free_space_reservation = free_space_reservation
        self._external_drives_repository = external_drives_repository

    def create(self, config, parallel_update, silent=False, hash_check=True):
        logger = DebugOnlyLoggerDecorator(self._logger) if silent else self._logger
        file_system = self._file_system_factory.create_for_config(config)
        target_path_repository = TargetPathRepository(config, file_system)
        workers_factory = DownloaderWorkersFactory(make_downloader_worker_context(
            job_system=self._job_system,
            waiter=self._waiter,
            logger=self._logger,
            http_gateway=self._http_gateway,
            file_system=file_system,
            target_path_repository=target_path_repository,
            installation_report=InstallationReportImpl(),
            file_download_reporter=self._file_download_reporter,
            free_space_reservation=self._free_space_reservation,
            external_drives_repository=self._external_drives_repository,
            target_paths_calculator_factory=TargetPathsCalculatorFactory(file_system, self._external_drives_repository),
            config=config
        ))
        return FileDownloader(
            parallel_update,
            hash_check,
            config,
            file_system,
            target_path_repository,
            logger,
            workers_factory,
            self._file_download_reporter,
            self._http_gateway,
            self._job_system
        )


class FileDownloader:
    def __init__(self, parallel_update, hash_check, config, file_system, target_path_repository, logger, workers_factory: 'DownloaderWorkersFactory', file_reporter: 'FileDownloadProgressReporter', http_gateway: HttpGateway, job_system: JobSystem):
        self._parallel_update = parallel_update
        self._hash_check = hash_check
        self._file_system = file_system
        self._target_path_repository = target_path_repository
        self._config = config
        self._logger = logger
        self._queued_files = {}
        self._unpacked_zips = {}
        self._correct_files = []
        self._failed_folders = []
        self._no_url_files = []
        self._file_reporter = file_reporter
        self._workers_factory = workers_factory
        self._http_gateway = http_gateway
        self._job_system = job_system

    def failed_folders(self):
        return self._failed_folders

    def queue_file(self, file_description, file_path):
        self._queued_files[file_path] = file_description

    def mark_unpacked_zip(self, zip_id, base_zips_url):
        self._unpacked_zips[zip_id] = base_zips_url

    def download_files(self, _):
        self._download()

        if self._file_system.is_file(FILE_MiSTer_new, use_cache=False):
            self._logger.print('')
            self._logger.print('Copying new MiSTer binary:')
            if self._file_system.is_file(FILE_MiSTer, use_cache=False):
                self._file_system.move(FILE_MiSTer, FILE_MiSTer_old)
            self._file_system.move(FILE_MiSTer_new, FILE_MiSTer)

            if self._file_system.is_file(FILE_MiSTer, use_cache=False):
                self._logger.print('New MiSTer binary copied.')
            else:
                # This error message should never happen.
                # If it happens it would be an unexpected case where file_system is not moving files correctly
                self._logger.print('CRITICAL ERROR!!! Could not restore the MiSTer binary!')
                self._logger.print('Please manually rename the file MiSTer.new as MiSTer')
                self._logger.print('Your system won\'nt be able to boot until you do so!')
                sys.exit(1)

    def _download(self):
        files_to_download = []
        skip_files = []
        for file_path, file_description in self._queued_files.items():
            if 'db' in file_description:
                files_to_download.append(file_path)
                continue

            try:
                will_download = self._do_we_have_to_download_the_file(file_path, file_description)
            except FolderCreationError as folder_path:
                self._logger.print('ERROR: Folder for file "%s" could not be created, skipping.' % file_path)
                self._logger.debug(folder_path)
                self._failed_folders.append(folder_path)
                continue

            if will_download:
                files_to_download.append(file_path)
            else:
                skip_files.append(file_path)

        self._check_downloaded_files(skip_files)
        self._workers_factory.prepare_workers()
        for path in files_to_download:
            description = self._queued_files[path]

            if 'db' in description:
                self._job_system.push_job(DbHeaderJob(description['db']))
            elif 'url' not in description:
                self._no_url_files.append(path)
                continue
            else:
                self._job_system.push_job(FetchFileJob(
                    path=path,
                    description=description,
                    hash_check=self._hash_check
                ))
        self._file_reporter.start_session()
        self._job_system.accomplish_pending_jobs()

        self._check_downloaded_files(self._file_reporter.report().downloaded_files())
        self._file_reporter.print_pending()

    def _do_we_have_to_download_the_file(self, file_path: str, file_description: Dict[str, Any]) -> bool:
        if self._hash_check and self._file_system.is_file(file_path):
            path_hash = self._file_system.hash(file_path)
            if path_hash == file_description['hash']:
                if 'zip_id' in file_description and file_description['zip_id'] in self._unpacked_zips:
                    self._logger.print('Unpacked: %s' % file_path)
                else:
                    self._logger.print('No changes: %s' % file_path)  # @TODO: This scenario might be redundant now, since it's also checked in the Online Importer
                return False
            else:
                self._logger.debug('%s: %s != %s' % (file_path, file_description['hash'], path_hash))

        self._file_system.make_dirs_parent(file_path)
        return True

    def _check_downloaded_files(self, files):
        for path in files:
            if path not in self._queued_files:
                continue
            self._correct_files.append(path)
            self._queued_files.pop(path)

    def errors(self):
        return self._file_reporter.report().failed_files() + self._no_url_files

    def correctly_downloaded_files(self):
        return self._correct_files

    def run_files(self):
        return self._file_reporter.report().fetch_started_files()


def context_from_curl_ssl(curl_ssl):
    context = ssl.create_default_context()

    if curl_ssl.startswith('--cacert '):
        cacert_file = curl_ssl[len('--cacert '):]
        context.load_verify_locations(cacert_file)
    elif curl_ssl == '--insecure':
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    return context

