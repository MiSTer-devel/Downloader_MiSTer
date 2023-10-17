# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>
import threading
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

from typing import List

from downloader.jobs.db_header_job import DbHeaderWorker
from downloader.jobs.download_db_worker import DownloadDbWorker
from downloader.jobs.fetch_file_worker2 import FetchFileWorker2
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.process_db_worker import ProcessDbWorker
from downloader.jobs.validate_file_worker import ValidateFileWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.validate_file_worker2 import ValidateFileWorker2
from downloader.jobs.worker_context import DownloaderWorkerContext, DownloaderWorker


class DownloaderWorkersFactory:
    def __init__(self, ctx: DownloaderWorkerContext):
        self._ctx = ctx
        self.FetchFileWorker = FetchFileWorker(self._ctx)
        self.FetchFileWorker2 = FetchFileWorker2(self._ctx)
        self.ValidateFileWorker = ValidateFileWorker(self._ctx)
        self.ValidateFileWorker2 = ValidateFileWorker2(self._ctx)
        self.DbHeaderWorker = DbHeaderWorker(self._ctx)
        self.DownloadDbWorker = DownloadDbWorker(self._ctx)
        self.OpenDbWorker = OpenDbWorker(self._ctx)
        self.ProcessDbWorker = ProcessDbWorker(self._ctx)

    def prepare_workers(self):
        workers: List[DownloaderWorker] = [
            self.FetchFileWorker,
            self.FetchFileWorker2,
            self.ValidateFileWorker,
            self.ValidateFileWorker2,
            self.DbHeaderWorker,
            self.DownloadDbWorker,
            self.OpenDbWorker,
            self.ProcessDbWorker,
        ]
        for w in workers:
            w.initialize()
