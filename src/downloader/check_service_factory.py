# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import atexit

from downloader.base_path_relocator import BasePathRelocator
from downloader.check_service import CheckService
from downloader.config import Config
from downloader.constants import HTTP_SOCKET_TIMEOUT, JOB_SYSTEM_INACTIVITY_TIMEOUT
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.file_system import FileSystemFactory
from downloader.http_gateway import HttpGateway
from downloader.interruptions import Interruptions
from downloader.job_system import ActivityTracker, JobSystem
from downloader.jobs.reporters import DownloaderProgressReporter, FileDownloadProgressReporter
from downloader.local_repository import LocalRepository
from downloader.logger import DebugOnlyLoggerDecorator, Logger, TopLogger
from downloader.migrations import migrations
from downloader.online_checker import OnlineChecker, OnlineCheckerWorkersFactory
from downloader.ssl_context import context_from_curl_ssl
from downloader.store_migrator import StoreMigrator
from downloader.update_output import UpdateOutput
from downloader.waiter import Waiter


class CheckServiceFactory:
    def __init__(self, logger: Logger, update_output: UpdateOutput, external_drives_repository_factory: ExternalDrivesRepositoryFactory) -> None:
        self._logger = logger
        self._update_output = update_output
        self._external_drives_repository_factory = external_drives_repository_factory

    @staticmethod
    def for_main(top_logger: TopLogger, update_output: UpdateOutput):
        return CheckServiceFactory(top_logger, update_output, ExternalDrivesRepositoryFactory())

    def create(self, config: Config):
        path_dictionary: dict[str, str] = dict()
        waiter = Waiter()
        activity_tracker = ActivityTracker()
        file_system_factory = FileSystemFactory(config, path_dictionary, self._logger, activity_tracker)
        system_file_system = file_system_factory.create_for_system_scope()
        external_drives_repository = self._external_drives_repository_factory.create(system_file_system, self._logger)
        store_migrator = StoreMigrator(migrations(config), self._logger)
        local_repository = LocalRepository(config, self._logger, system_file_system, store_migrator, external_drives_repository)

        ssl_ctx, ssl_err = context_from_curl_ssl(config['curl_ssl'])
        if ssl_err is not None:
            self._logger.debug(ssl_err)
            self._logger.print('WARNING! Ignoring SSL parameters...')
        http_gateway = HttpGateway(
            ssl_ctx=ssl_ctx,
            read_timeout=HTTP_SOCKET_TIMEOUT,
            logger=DebugOnlyLoggerDecorator(self._logger) if config['http_logging'] else None,
            config=config['http_config']
        )
        atexit.register(http_gateway.cleanup)

        file_download_reporter = FileDownloadProgressReporter(
            self._logger,
            Interruptions(file_system_factory, http_gateway),
            self._update_output
        )
        job_system = JobSystem(
            reporter=DownloaderProgressReporter(self._logger, [file_download_reporter]),
            logger=self._logger,
            activity_tracker=activity_tracker,
            max_threads=config['downloader_threads_limit'],
            max_tries=config['downloader_retries'],
            max_timeout=JOB_SYSTEM_INACTIVITY_TIMEOUT,
        )
        online_checker_workers_factory = OnlineCheckerWorkersFactory(
            worker_context=job_system,
            progress_reporter=file_download_reporter,
            file_system=system_file_system,
            http_gateway=http_gateway,
            logger=self._logger,
            file_download_reporter=file_download_reporter,
            local_repository=local_repository,
            base_path_relocator=BasePathRelocator(config, file_system_factory, waiter, self._logger),
            config=config,
        )
        online_checker = OnlineChecker(
            logger=self._logger,
            job_system=job_system,
            worker_factory=online_checker_workers_factory,
        )

        return CheckService(
            config,
            online_checker,
            local_repository,
            system_file_system,
            self._update_output,
            self._logger,
        )
