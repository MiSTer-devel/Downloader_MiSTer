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

from downloader.base_path_relocator import BasePathRelocator
from downloader.certificates_fix import CertificatesFix
from downloader.constants import K_DOWNLOADER_TIMEOUT, K_DEBUG, K_CURL_SSL, K_DOWNLOADER_THREADS_LIMIT, K_DOWNLOADER_RETRIES, K_IS_PC_LAUNCHER, FILE_MiSTer_version
from downloader.db_gateway import DbGateway
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.file_downloader import FileDownloaderFactory, context_from_curl_ssl
from downloader.file_filter import FileFilterFactory
from downloader.file_system import FileSystemFactory
from downloader.free_space_reservation import LinuxFreeSpaceReservation, UnlimitedFreeSpaceReservation
from downloader.full_run_service import FullRunService
from downloader.http_gateway import HttpGateway
from downloader.importer_command import ImporterCommandFactory
from downloader.interruptions import Interruptions
from downloader.job_system import JobSystem
from downloader.jobs.reporters import DownloaderProgressReporter, FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorkerContext, make_downloader_worker_context
from downloader.logger import DebugOnlyLoggerDecorator
from downloader.os_utils import LinuxOsUtils
from downloader.storage_priority_resolver import StoragePriorityResolver
from downloader.linux_updater import LinuxUpdater
from downloader.local_repository import LocalRepository
from downloader.migrations import migrations
from downloader.offline_importer import OfflineImporter
from downloader.online_importer import OnlineImporter
from downloader.path_resolver import PathResolverFactory
from downloader.reboot_calculator import RebootCalculator
from downloader.store_migrator import StoreMigrator
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.waiter import Waiter
import atexit


class FullRunServiceFactory:
    def __init__(self, logger, local_repository_provider, external_drives_repository_factory=None):
        self._logger = logger
        self._external_drives_repository_factory = external_drives_repository_factory or ExternalDrivesRepositoryFactory()
        self._local_repository_provider = local_repository_provider

    def create(self, config):
        path_dictionary = dict()
        waiter = Waiter()
        file_system_factory = FileSystemFactory(config, path_dictionary, self._logger)
        system_file_system = file_system_factory.create_for_system_scope()
        external_drives_repository = self._external_drives_repository_factory.create(system_file_system, self._logger)
        storage_priority_resolver_factory = StoragePriorityResolver(file_system_factory, external_drives_repository)
        path_resolver_factory = PathResolverFactory(storage_priority_resolver_factory, path_dictionary)
        store_migrator = StoreMigrator(migrations(config, file_system_factory, path_resolver_factory), self._logger)

        local_repository = LocalRepository(config, self._logger, system_file_system, store_migrator, external_drives_repository)

        self._local_repository_provider.initialize(local_repository)
        importer_command_factory = ImporterCommandFactory(config)

        http_connection_timeout = config[K_DOWNLOADER_TIMEOUT] / 4 if config[K_DOWNLOADER_TIMEOUT] > 60 else 15

        http_gateway = HttpGateway(
            ssl_ctx=context_from_curl_ssl(config[K_CURL_SSL]),
            timeout=http_connection_timeout,
            logger=DebugOnlyLoggerDecorator(self._logger) if config[K_DEBUG] else None
        )
        atexit.register(http_gateway.cleanup)
        installation_report = InstallationReportImpl()
        interrupts = Interruptions(file_system_factory)
        file_download_reporter = FileDownloadProgressReporter(self._logger, waiter, interrupts, installation_report)
        job_system = JobSystem(
            reporter=DownloaderProgressReporter(self._logger, [file_download_reporter]),
            logger=self._logger,
            max_threads=config[K_DOWNLOADER_THREADS_LIMIT],
            max_tries=config[K_DOWNLOADER_RETRIES],
            max_timeout=config[K_DOWNLOADER_TIMEOUT] * 2,
        )

        file_filter_factory = FileFilterFactory(self._logger)
        free_space_reservation = LinuxFreeSpaceReservation(logger=self._logger, config=config) if system_file_system.is_file(FILE_MiSTer_version) else UnlimitedFreeSpaceReservation()
        file_downloader_factory = FileDownloaderFactory(file_system_factory, waiter, self._logger, job_system, file_download_reporter, file_download_reporter, http_gateway, free_space_reservation, external_drives_repository)
        db_gateway = DbGateway(config, system_file_system, file_downloader_factory, self._logger)
        offline_importer = OfflineImporter(file_system_factory, file_downloader_factory, self._logger)
        online_importer = OnlineImporter(file_filter_factory, file_system_factory, file_downloader_factory, path_resolver_factory, local_repository, external_drives_repository, free_space_reservation, waiter, self._logger)
        linux_updater = LinuxUpdater(config, system_file_system, file_downloader_factory, self._logger)

        workers_ctx = make_downloader_worker_context(
            job_ctx=job_system,
            waiter=waiter,
            logger=self._logger,
            http_gateway=http_gateway,
            file_system=system_file_system,
            target_path_repository=None,
            installation_report=installation_report,
            progress_reporter=file_download_reporter,
            file_download_session_logger=file_download_reporter,
            free_space_reservation=free_space_reservation,
            external_drives_repository=external_drives_repository,
            target_paths_calculator_factory=TargetPathsCalculatorFactory(system_file_system, external_drives_repository),
            config=config
        )

        return FullRunService(
            config,
            self._logger,
            local_repository,
            db_gateway,
            offline_importer,
            online_importer,
            linux_updater,
            RebootCalculator(config, self._logger, system_file_system),
            BasePathRelocator(file_system_factory, waiter, self._logger),
            CertificatesFix(config, system_file_system, waiter, self._logger),
            external_drives_repository,
            LinuxOsUtils(),
            waiter,
            importer_command_factory,
            job_system,
            workers_ctx
        )
