# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from downloader.config import Config
from downloader.file_filter import FileFilterFactory
from downloader.file_system import FileSystem
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobContext, ProgressReporter
from downloader.jobs.abort_worker import AbortWorker
from downloader.jobs.copy_data_worker import CopyDataWorker
from downloader.jobs.fetch_data_worker import FetchDataWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.load_local_store_sigs_worker import LoadLocalStoreSigsWorker
from downloader.jobs.load_local_store_worker import LoadLocalStoreWorker
from downloader.jobs.mix_store_and_db_worker import MixStoreAndDbWorker
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.open_zip_contents_worker import OpenZipContentsWorker
from downloader.jobs.open_zip_summary_worker import OpenZipSummaryWorker
from downloader.jobs.process_db_main_worker import ProcessDbMainWorker
from downloader.jobs.reporters import FileDownloadSessionLogger, InstallationReportImpl
from downloader.jobs.wait_db_zips_worker import WaitDbZipsWorker
from downloader.jobs.process_db_index_worker import ProcessDbIndexWorker, ProcessIndexCtx
from downloader.jobs.process_zip_index_worker import ProcessZipIndexWorker
from downloader.jobs.worker_context import JobErrorCtx
from downloader.local_repository import LocalRepository
from downloader.logger import Logger
from downloader.target_path_calculator import TargetPathsCalculatorFactory


class OnlineImporterWorkersFactory:
    def __init__(self, worker_context: JobContext, progress_reporter: ProgressReporter, file_system: FileSystem, http_gateway: HttpGateway, logger: Logger, file_download_session_logger: FileDownloadSessionLogger, installation_report: InstallationReportImpl, file_filter_factory: FileFilterFactory, target_paths_calculator_factory: TargetPathsCalculatorFactory, free_space_reservation: FreeSpaceReservation, local_repository: LocalRepository, base_path_relocator: BasePathRelocator, config: Config, error_ctx: JobErrorCtx):
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter
        self._file_system = file_system
        self._http_gateway = http_gateway
        self._logger = logger
        self._file_download_session_logger = file_download_session_logger
        self._installation_report = installation_report
        self._file_filter_factory = file_filter_factory
        self._target_paths_calculator_factory = target_paths_calculator_factory
        self._free_space_reservation = free_space_reservation
        self._local_repository = local_repository
        self._base_path_relocator = base_path_relocator
        self._config = config
        self._error_ctx = error_ctx

    def create_workers(self):
        process_index_ctx = ProcessIndexCtx(
            error_ctx=self._error_ctx,
            file_system=self._file_system,
            logger=self._logger,
            installation_report=self._installation_report,
            file_filter_factory=self._file_filter_factory,
            target_paths_calculator_factory=self._target_paths_calculator_factory,
            file_download_session_logger=self._file_download_session_logger,
            free_space_reservation=self._free_space_reservation,
        )
        return [
            AbortWorker(
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
            ),
            CopyDataWorker(
                file_system=self._file_system,
                progress_reporter=self._progress_reporter,
            ),
            FetchFileWorker(
                progress_reporter=self._progress_reporter,
                http_gateway=self._http_gateway,
                file_system=self._file_system,
                timeout=self._config["downloader_timeout"],
            ),
            FetchDataWorker(
                http_gateway=self._http_gateway,
                file_system=self._file_system,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
                timeout=self._config["downloader_timeout"],
            ),
            OpenDbWorker(
                file_system=self._file_system,
                logger=self._logger,
                file_download_session_logger=self._file_download_session_logger,
                installation_report=self._installation_report,
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
                config=self._config,
            ),
            MixStoreAndDbWorker(
                logger=self._logger,
                installation_report=self._installation_report,
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
            ),
            ProcessDbIndexWorker(
                logger=self._logger,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
                process_index_ctx=process_index_ctx,
            ),
            WaitDbZipsWorker(
                logger=self._logger,
                installation_report=self._installation_report,
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
            ),
            ProcessDbMainWorker(
                logger=self._logger,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
            ),
            ProcessZipIndexWorker(
                logger=self._logger,
                target_paths_calculator_factory=self._target_paths_calculator_factory,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
                process_index_ctx=process_index_ctx,
            ),
            LoadLocalStoreSigsWorker(
                logger=self._logger,
                local_repository=self._local_repository,
                progress_reporter=self._progress_reporter,
            ),
            LoadLocalStoreWorker(
                logger=self._logger,
                local_repository=self._local_repository,
                base_path_relocator=self._base_path_relocator,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
            ),
            OpenZipSummaryWorker(
                file_system=self._file_system,
                logger=self._logger,
                progress_reporter=self._progress_reporter,
                error_ctx=self._error_ctx,
            ),
            OpenZipContentsWorker(
                logger=self._logger,
                progress_reporter=self._progress_reporter,
                process_index_ctx=process_index_ctx,
            ),
        ]
