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
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.open_zip_contents_worker import OpenZipContentsWorker
from downloader.jobs.open_zip_summary_worker import OpenZipSummaryWorker
from downloader.jobs.process_db_main_worker import ProcessDbMainWorker
from downloader.jobs.wait_db_zips_worker import WaitDbZipsWorker
from downloader.jobs.process_db_index_worker import ProcessDbIndexWorker
from downloader.jobs.process_zip_index_worker import ProcessZipIndexWorker
from downloader.jobs.validate_file_worker import ValidateFileWorker
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext


def make_workers(ctx: DownloaderWorkerContext) -> List[DownloaderWorker]:
    return [
        CopyFileWorker(ctx),
        FetchFileWorker(progress_reporter=ctx.progress_reporter, http_gateway=ctx.http_gateway, file_system=ctx.file_system, timeout=ctx.config['downloader_timeout']),
        ValidateFileWorker(progress_reporter=ctx.progress_reporter, file_system=ctx.file_system),
        OpenDbWorker(ctx),
        ProcessDbIndexWorker(ctx),
        WaitDbZipsWorker(ctx),
        ProcessDbMainWorker(ctx),
        ProcessZipIndexWorker(ctx),
        OpenZipSummaryWorker(ctx),
        OpenZipContentsWorker(ctx)
    ]
