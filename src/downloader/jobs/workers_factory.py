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
from downloader.jobs.process_db_zips_waiter_worker import ProcessDbZipsWaiterWorker
from downloader.jobs.process_index_worker import ProcessIndexWorker
from downloader.jobs.process_zip_worker import ProcessZipWorker
from downloader.jobs.validate_file_worker import ValidateFileWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.validate_file_worker2 import ValidateFileWorker2
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext


def make_workers(ctx: DownloaderWorkerContext) -> List[DownloaderWorker]:
    return [
        CopyFileWorker(ctx),
        FetchFileWorker(ctx),
        FetchFileWorker2(progress_reporter=ctx.progress_reporter, http_gateway=ctx.http_gateway, file_system=ctx.file_system, timeout=ctx.config['downloader_timeout']),
        ValidateFileWorker(ctx),
        ValidateFileWorker2(progress_reporter=ctx.progress_reporter, file_system=ctx.file_system),
        DbHeaderWorker(ctx),
        DownloadDbWorker(ctx),
        OpenDbWorker(ctx),
        ProcessIndexWorker(ctx),
        ProcessDbZipsWaiterWorker(ctx),
        ProcessDbWorker(ctx),
        ProcessZipWorker(ctx),
        OpenZipIndexWorker(ctx),
        OpenZipContentsWorker(ctx)
    ]
