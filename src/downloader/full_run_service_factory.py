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

import ssl
from typing import Dict
from downloader.base_path_relocator import BasePathRelocator
from downloader.certificates_fix import CertificatesFix
from downloader.config import Config
from downloader.constants import FILE_MiSTer_version
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.file_filter import FileFilterFactory
from downloader.file_system import FileSystemFactory
from downloader.free_space_reservation import LinuxFreeSpaceReservation, UnlimitedFreeSpaceReservation
from downloader.full_run_service import FullRunService
from downloader.http_gateway import HttpGateway
from downloader.interruptions import Interruptions
from downloader.job_system import JobSystem
from downloader.jobs.fetch_file_worker import SafeFileFetcher
from downloader.jobs.reporters import DownloaderProgressReporter, FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorkerContext
from downloader.logger import DebugOnlyLoggerDecorator, Logger, FilelogManager, ConfigLogManager, \
    TopLogger
from downloader.os_utils import LinuxOsUtils
from downloader.linux_updater import LinuxUpdater
from downloader.local_repository import LocalRepository
from downloader.migrations import migrations
from downloader.online_importer import OnlineImporter
from downloader.reboot_calculator import RebootCalculator
from downloader.store_migrator import StoreMigrator
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.waiter import Waiter
import atexit


class FullRunServiceFactory:
    def __init__(self, logger: Logger, filelog_manager: FilelogManager, printlog_manager: ConfigLogManager, external_drives_repository_factory=None):
        self._logger = logger
        self._filelog_manager = filelog_manager
        self._printlog_manager = printlog_manager
        self._external_drives_repository_factory = external_drives_repository_factory or ExternalDrivesRepositoryFactory()


    @staticmethod
    def for_main(top_logger: TopLogger):
        return FullRunServiceFactory(top_logger, top_logger.file_logger, top_logger)

    def create(self, config: Config):
        path_dictionary: Dict[str, str] = dict()
        waiter = Waiter()
        file_system_factory = FileSystemFactory(config, path_dictionary, self._logger)
        system_file_system = file_system_factory.create_for_system_scope()
        external_drives_repository = self._external_drives_repository_factory.create(system_file_system, self._logger)
        store_migrator = StoreMigrator(migrations(config, file_system_factory), self._logger)
        local_repository = LocalRepository(config, self._logger, system_file_system, store_migrator, external_drives_repository)

        http_connection_timeout = config['downloader_timeout'] / 4 if config['downloader_timeout'] > 60 else 15

        http_gateway = HttpGateway(
            ssl_ctx=context_from_curl_ssl(config['curl_ssl']),
            timeout=http_connection_timeout,
            logger=DebugOnlyLoggerDecorator(self._logger) if config['http_logging'] else None
        )
        atexit.register(http_gateway.cleanup)
        safe_file_fetcher = SafeFileFetcher(config, system_file_system, self._logger, http_gateway, waiter)
        installation_report = InstallationReportImpl()
        interrupts = Interruptions(file_system_factory)
        file_download_reporter = FileDownloadProgressReporter(self._logger, waiter, interrupts, installation_report)
        job_system = JobSystem(
            reporter=DownloaderProgressReporter(self._logger, [file_download_reporter]),
            logger=self._logger,
            max_threads=config['downloader_threads_limit'],
            max_tries=config['downloader_retries'],
            max_timeout=config['downloader_timeout'] * 2,
        )

        file_filter_factory = FileFilterFactory(self._logger)
        free_space_reservation = LinuxFreeSpaceReservation(logger=self._logger, config=config) if system_file_system.is_file(FILE_MiSTer_version) else UnlimitedFreeSpaceReservation()
        linux_updater = LinuxUpdater(self._logger, config, system_file_system, safe_file_fetcher)

        workers_ctx = DownloaderWorkerContext(
            job_ctx=job_system,
            waiter=waiter,
            logger=self._logger,
            http_gateway=http_gateway,
            file_system=system_file_system,
            installation_report=installation_report,
            progress_reporter=file_download_reporter,
            file_download_session_logger=file_download_reporter,
            free_space_reservation=free_space_reservation,
            external_drives_repository=external_drives_repository,
            file_filter_factory=file_filter_factory,
            target_paths_calculator_factory=TargetPathsCalculatorFactory(system_file_system, external_drives_repository),
            config=config
        )
        online_importer = OnlineImporter(logger=self._logger, job_system=job_system, worker_ctx=workers_ctx, free_space_reservation=free_space_reservation)

        instance = FullRunService(
            config,
            self._logger,
            self._filelog_manager,
            self._printlog_manager,
            local_repository,
            online_importer,
            linux_updater,
            RebootCalculator(config, self._logger, system_file_system),
            BasePathRelocator(config, file_system_factory, waiter, self._logger),
            CertificatesFix(config, system_file_system, waiter, self._logger),
            external_drives_repository,
            LinuxOsUtils(),
            waiter
        )
        instance.configure_components()
        return instance


def context_from_curl_ssl(curl_ssl):
    context = ssl.create_default_context()

    if curl_ssl.startswith('--cacert '):
        cacert_file = curl_ssl[len('--cacert '):]
        context.load_verify_locations(cacert_file)
    elif curl_ssl == '--insecure':
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    return context
