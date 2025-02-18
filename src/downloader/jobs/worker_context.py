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
from enum import Enum, auto

from downloader.config import Config
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_filter import FileFilterFactory
from downloader.file_system import FileSystem
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.http_gateway import HttpGateway
from downloader.job_system import Job, Worker, ProgressReporter, JobContext
from downloader.jobs.reporters import InstallationReportImpl, FileDownloadSessionLogger
from downloader.logger import Logger
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.waiter import Waiter


class DownloaderWorkerFailPolicy(Enum):
    FAIL_FAST = auto()
    FAULT_TOLERANT = auto()


class NilJob(Job): type_id = -1


@dataclass
class DownloaderWorkerContext:
    job_ctx: JobContext
    http_gateway: HttpGateway
    logger: Logger
    file_system: FileSystem
    waiter: Waiter
    file_download_session_logger: FileDownloadSessionLogger
    progress_reporter: ProgressReporter
    installation_report: InstallationReportImpl
    free_space_reservation: FreeSpaceReservation
    external_drives_repository: ExternalDrivesRepository
    file_filter_factory: FileFilterFactory
    target_paths_calculator_factory: TargetPathsCalculatorFactory
    config: Config
    fail_policy: DownloaderWorkerFailPolicy = DownloaderWorkerFailPolicy.FAULT_TOLERANT

    def swallow_error(self, e: Exception, print: bool = True):
        if self.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
            raise e
        self.logger.debug(e)
        if print: self.logger.print(f"ERROR: {e}")


class DownloaderWorker(Worker):
    @abstractmethod
    def job_type_id(self) -> int:
        """Returns the type id of the job this worker operates on."""


class DownloaderWorkerBase(DownloaderWorker, ABC):
    def __init__(self, ctx: DownloaderWorkerContext): self._ctx = ctx

