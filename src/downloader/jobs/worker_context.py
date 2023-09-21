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
from dataclasses import dataclass

from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobSystem, Worker
from downloader.jobs.reporters import FileDownloadProgressReporter
from downloader.logger import Logger
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


class DownloaderWorker(Worker):
    def __init__(self, ctx: DownloaderWorkerContext):
        self._ctx = ctx

    @abstractmethod
    def initialize(self):
        """Initialize the worker"""
