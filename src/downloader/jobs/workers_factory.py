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

from typing import Dict, Any, List

from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobSystem
from downloader.jobs.db_header_job import DbHeaderWorker
from downloader.jobs.validate_file_worker import ValidateFileWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.reporters import FileDownloadProgressReporter
from downloader.jobs.worker_context import DownloaderWorkerContext, DownloaderWorker
from downloader.logger import Logger
from downloader.target_path_repository import TargetPathRepository
from downloader.waiter import Waiter


class DownloaderWorkersFactory:
    def __init__(self, config: Dict[str, Any], waiter: Waiter, logger: Logger, file_system: FileSystem, target_path_repository: TargetPathRepository, file_download_reporter: FileDownloadProgressReporter, job_system: JobSystem, http_gateway: HttpGateway):
        self._config = config
        self._waiter = waiter
        self._logger = logger
        self._file_system = file_system
        self._target_path_repository = target_path_repository
        self._file_download_reporter = file_download_reporter
        self._job_system = job_system
        self._http_gateway = http_gateway

    def prepare_workers(self):
        work_ctx = DownloaderWorkerContext(
            job_system=self._job_system,
            waiter=self._waiter,
            logger=self._logger,
            http_gateway=self._http_gateway,
            file_system=self._file_system,
            target_path_repository=self._target_path_repository,
            file_download_reporter=self._file_download_reporter
        )
        workers: List[DownloaderWorker] = [
            FetchFileWorker(work_ctx),
            ValidateFileWorker(work_ctx),
            DbHeaderWorker(work_ctx),
        ]
        for w in workers:
            w.initialize()
