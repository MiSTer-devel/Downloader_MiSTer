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

from downloader.job_system import WorkerResult
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.worker_context import DownloaderWorkerContext, DownloaderWorker
from downloader.jobs.workers_factory import make_workers as production_make_workers
from downloader.jobs.fetch_file_worker2 import FetchFileWorker2 as ProductionFetchFileWorker2
from downloader.jobs.fetch_file_worker import FetchFileWorker as ProductionFetchFileWorker
from test.fake_http_gateway import set_current_job


def make_workers(ctx: DownloaderWorkerContext) -> List[DownloaderWorker]:
    replacement_workers = [FetchFileWorker2(ctx), FetchFileWorker(ctx)]
    replacement_type_ids = {r.job_type_id() for r in replacement_workers}
    workers = [w for w in production_make_workers(ctx) if w.job_type_id() not in replacement_type_ids]
    return [*workers, *replacement_workers]


class FetchFileWorker2(ProductionFetchFileWorker2):
    def operate_on(self, job: FetchFileJob2) -> WorkerResult:
        set_current_job(job)
        result = super().operate_on(job)
        set_current_job(None)
        return result


class FetchFileWorker(ProductionFetchFileWorker):
    def operate_on(self, job: FetchFileJob) -> WorkerResult:
        set_current_job(job)
        result = super().operate_on(job)
        set_current_job(None)
        return result
