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

from abc import abstractmethod, ABC
from dataclasses import dataclass
import threading
from typing import Dict, Any, Tuple, Set, List

from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.http_gateway import HttpGateway
from downloader.job_system import Worker, ProgressReporter, JobContext
from downloader.path_package import PathPackage
from downloader.jobs.reporters import InstallationReportImpl, FileDownloadSessionLogger
from downloader.logger import Logger
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.target_path_repository import TargetPathRepository
from downloader.waiter import Waiter


@dataclass
class DownloaderWorkerContext:
    job_ctx: JobContext
    http_gateway: HttpGateway
    logger: Logger
    target_path_repository: TargetPathRepository
    file_system: FileSystem
    waiter: Waiter
    file_download_session_logger: FileDownloadSessionLogger
    progress_reporter: ProgressReporter
    installation_report: InstallationReportImpl
    free_space_reservation: FreeSpaceReservation
    external_drives_repository: ExternalDrivesRepository
    target_paths_calculator_factory: TargetPathsCalculatorFactory
    config: Dict[str, Any]
    pending_removals: 'PendingRemovals'
    top_lock: threading.Lock


def make_downloader_worker_context(job_ctx: JobContext, http_gateway: HttpGateway, logger: Logger, target_path_repository: TargetPathRepository, file_system: FileSystem, waiter: Waiter, progress_reporter: ProgressReporter, file_download_session_logger: FileDownloadSessionLogger, installation_report: InstallationReportImpl, free_space_reservation: FreeSpaceReservation, external_drives_repository: ExternalDrivesRepository, target_paths_calculator_factory: TargetPathsCalculatorFactory, config: Dict[str, Any]) -> DownloaderWorkerContext:
    return DownloaderWorkerContext(
        job_ctx=job_ctx,
        http_gateway=http_gateway,
        logger=logger,
        target_path_repository=target_path_repository,
        file_system=file_system,
        waiter=waiter,
        progress_reporter=progress_reporter,
        file_download_session_logger=file_download_session_logger,
        installation_report=installation_report,
        free_space_reservation=free_space_reservation,
        external_drives_repository=external_drives_repository,
        target_paths_calculator_factory=target_paths_calculator_factory,
        config=config,
        pending_removals=PendingRemovals(),
        top_lock=threading.Lock(),
    )

class DownloaderWorker(Worker):
    @abstractmethod
    def job_type_id(self) -> int:
        """Returns the type id of the job this worker operates on."""


class DownloaderWorkerBase(DownloaderWorker, ABC):
    def __init__(self, ctx: DownloaderWorkerContext): self._ctx = ctx


class PendingRemovals:
    def __init__(self):
        self._directories = dict()
        self._files = dict()

    def queue_directory_removal(self, pkg: PathPackage, db_id: str) -> None: self._directories.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)
    def queue_file_removal(self, pkg: PathPackage, db_id: str) -> None: self._files.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)

    def consume_files(self) -> List[Tuple[PathPackage, Set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._files.values()], key=lambda x: x[0].rel_path)
        self._files.clear()
        return result

    def consume_directories(self) -> List[Tuple[PathPackage, Set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._directories.values()], key=lambda x: len(x[0].rel_path))
        self._directories.clear()
        return result
