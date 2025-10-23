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

from typing import List

from downloader.jobs.abort_worker import AbortWorker
from downloader.jobs.copy_data_worker import CopyDataWorker
from downloader.jobs.fetch_data_worker import FetchDataWorker
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.load_local_store_sigs_worker import LoadLocalStoreSigsWorker
from downloader.jobs.load_local_store_worker import LoadLocalStoreWorker
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.open_zip_contents_worker import OpenZipContentsWorker
from downloader.jobs.open_zip_summary_worker import OpenZipSummaryWorker
from downloader.jobs.process_db_main_worker import ProcessDbMainWorker
from downloader.jobs.wait_db_zips_worker import WaitDbZipsWorker
from downloader.jobs.process_db_index_worker import ProcessDbIndexWorker
from downloader.jobs.process_zip_index_worker import ProcessZipIndexWorker
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext


def make_workers(ctx: DownloaderWorkerContext) -> List[DownloaderWorker]:
    return [
        AbortWorker(ctx),
        CopyDataWorker(ctx),
        FetchFileWorker(progress_reporter=ctx.progress_reporter, http_gateway=ctx.http_gateway, file_system=ctx.file_system, timeout=ctx.config['downloader_timeout']),
        FetchDataWorker(ctx, timeout=ctx.config['downloader_timeout']),
        OpenDbWorker(ctx),
        ProcessDbIndexWorker(ctx),
        WaitDbZipsWorker(ctx),
        ProcessDbMainWorker(ctx),
        ProcessZipIndexWorker(ctx),
        LoadLocalStoreSigsWorker(ctx),
        LoadLocalStoreWorker(ctx),
        OpenZipSummaryWorker(ctx),
        OpenZipContentsWorker(ctx),
    ]
