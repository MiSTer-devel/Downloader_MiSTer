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

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, Set, List
import threading

from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobSystem, Worker
from downloader.jobs.path_package import PathPackage
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.logger import Logger
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.target_path_repository import TargetPathRepository
from downloader.waiter import Waiter


@dataclass
class DownloaderWorkerContext:
    job_system: JobSystem
    http_gateway: HttpGateway
    logger: Logger
    target_path_repository: TargetPathRepository
    file_system: FileSystem
    waiter: Waiter
    file_download_reporter: FileDownloadProgressReporter
    installation_report: InstallationReportImpl
    free_space_reservation: FreeSpaceReservation
    external_drives_repository: ExternalDrivesRepository
    target_paths_calculator_factory: TargetPathsCalculatorFactory
    config: Dict[str, Any]
    zip_barrier_lock: 'ZipBarrierLock' = field(default_factory=lambda: ZipBarrierLock())
    pending_removals: 'PendingRemovals' = field(default_factory=lambda: PendingRemovals())


class DownloaderWorker(Worker):
    def __init__(self, ctx: DownloaderWorkerContext):
        self._ctx = ctx

    @abstractmethod
    def initialize(self):
        """Initialize the worker"""


class ZipBarrierLock:
    def __init__(self):
        self._lock = threading.Lock()
        self._zips_by_db = dict()

    def require_zip(self, db_id: str, zip_id: str):
        with self._lock: self._db_zips(db_id).add(zip_id)

    def release_zip(self, db_id: str, zip_id: str):
        with self._lock: self._db_zips(db_id).remove(zip_id)

    def release_all_zips(self, db_id: str):
        with self._lock: self._db_zips(db_id).clear()

    def is_barrier_free(self, db_id: str):
        with self._lock: return len(self._db_zips(db_id)) == 0

    def _db_zips(self, db_id: str): return self._zips_by_db.setdefault(db_id, set())


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
