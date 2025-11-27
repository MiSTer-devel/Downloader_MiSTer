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

from downloader.job_system import WorkerResult, Job
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_data_worker import FetchDataWorker
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.worker_context import DownloaderWorker
from downloader.online_importer_workers_factory import OnlineImporterWorkersFactory as ProductionOnlineImporterWorkersFactory
from test.fake_http_gateway import FakeHttpGateway


class OnlineImporterWorkersFactory(ProductionOnlineImporterWorkersFactory):
    def create_workers(self):
        replacement_workers = []
        if isinstance(self._http_gateway, FakeHttpGateway):
            fake_http: FakeHttpGateway = self._http_gateway
            replacement_workers.extend([
                FakeWorkerDecorator(FetchFileWorker(
                    progress_reporter=self._progress_reporter, http_gateway=fake_http, file_system=self._file_system,
                    timeout=self._config['downloader_timeout'],
                ), fake_http),
                FakeWorkerDecorator(FetchDataWorker(
                    http_gateway=fake_http,
                    file_system=self._file_system,
                    progress_reporter=self._progress_reporter,
                    error_ctx=self._error_ctx,
                    timeout=self._config['downloader_timeout'],
                ), fake_http),
            ])

        replacement_type_ids = {r.job_type_id() for r in replacement_workers}
        workers = [w for w in super().create_workers() if w.job_type_id() not in replacement_type_ids]
        return [*workers, *replacement_workers]


class FakeWorkerDecorator(DownloaderWorker):
    def __init__(self, worker: DownloaderWorker, fake_http: FakeHttpGateway):
        self._worker = worker
        self._fake_http = fake_http

    def job_type_id(self) -> int: return self._worker.job_type_id()
    def operate_on(self, job: Job) -> WorkerResult:
        if isinstance(job, FetchFileJob):
            self._fake_http.set_file_ctx({
                'description': {**job.pkg.description},
                'path': job.pkg.full_path,
                'info': job.pkg.rel_path
            })
        elif isinstance(job, FetchDataJob):
            self._fake_http.set_file_ctx({
                'description': {**job.description},
                'path': None,
                'info': None
            })
        try:
            return self._worker.operate_on(job)
        finally:
            self._fake_http.set_file_ctx(None)

