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

from downloader.job_system import WorkerResult, Job
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorkerContext, DownloaderWorker
from downloader.jobs.workers_factory import make_workers as production_make_workers
from downloader.jobs.fetch_file_worker import FetchFileWorker
from test.fake_http_gateway import FakeHttpGateway


def make_workers(ctx: DownloaderWorkerContext) -> List[DownloaderWorker]:
    replacement_workers = []
    if isinstance(ctx.http_gateway, FakeHttpGateway):
        fake_http: FakeHttpGateway = ctx.http_gateway
        replacement_workers.extend([
            FakeWorkerDecorator(FetchFileWorker(
                progress_reporter=ctx.progress_reporter, http_gateway=fake_http, file_system=ctx.file_system, timeout=ctx.config['downloader_timeout'],
            ), fake_http),
        ])

    replacement_type_ids = {r.job_type_id() for r in replacement_workers}
    workers = [w for w in production_make_workers(ctx) if w.job_type_id() not in replacement_type_ids]
    return [*workers, *replacement_workers]


class FakeWorkerDecorator(DownloaderWorker):
    def __init__(self, worker: DownloaderWorker, fake_http: FakeHttpGateway):
        self._worker = worker
        self._fake_http = fake_http

    def job_type_id(self) -> int: return self._worker.job_type_id()
    def operate_on(self, job: Job) -> WorkerResult:
        if isinstance(job, FetchFileJob):
            if isinstance(job.after_job, ValidateFileJob):
                description = {**job.after_job.description}
            else:
                description = None
            self._fake_http.set_file_ctx({
                'description': description,
                'path': job.temp_path,
                'info': job.info
            })
        try:
            return self._worker.operate_on(job)
        finally:
            self._fake_http.set_file_ctx(None)
