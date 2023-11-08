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

from typing import List

from downloader.jobs.copy_file_worker import CopyFileWorker
from downloader.jobs.db_header_job import DbHeaderWorker
from downloader.jobs.download_db_worker import DownloadDbWorker
from downloader.jobs.fetch_file_worker2 import FetchFileWorker2
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.open_zip_contents_worker import OpenZipContentsWorker
from downloader.jobs.open_zip_index_worker import OpenZipIndexWorker
from downloader.jobs.process_db_worker import ProcessDbWorker
from downloader.jobs.process_index_worker import ProcessIndexWorker
from downloader.jobs.process_zip_worker import ProcessZipWorker
from downloader.jobs.validate_file_worker import ValidateFileWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.validate_file_worker2 import ValidateFileWorker2
from downloader.jobs.worker_context import DownloaderWorkerContext, DownloaderWorker


class DownloaderWorkersFactory:
    def __init__(self, ctx: DownloaderWorkerContext):
        self._ctx = ctx

    def prepare_workers(self):
        workers: List[DownloaderWorker] = [
            CopyFileWorker(self._ctx),
            FetchFileWorker(self._ctx),
            FetchFileWorker2(self._ctx),
            ValidateFileWorker(self._ctx),
            ValidateFileWorker2(self._ctx),
            DbHeaderWorker(self._ctx),
            DownloadDbWorker(self._ctx),
            OpenDbWorker(self._ctx),
            ProcessIndexWorker(self._ctx),
            ProcessDbWorker(self._ctx),
            ProcessZipWorker(self._ctx),
            OpenZipIndexWorker(self._ctx),
            OpenZipContentsWorker(self._ctx)
        ]
        for w in workers:
            w.initialize()
