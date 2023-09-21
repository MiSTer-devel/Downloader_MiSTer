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

from typing import Dict, Any

from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadException


class FetchFileWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(FetchFileJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: FetchFileJob):
        file_path, description = job.path, job.description
        self._fetch_file(file_path, description)
        self._ctx.job_system.push_job(ValidateFileJob(fetch_job=job), priority=1)

    def _fetch_file(self, file_path: str, description: Dict[str, Any]):
        target_path = self._ctx.file_system.download_target_path(self._ctx.target_path_repository.create_target(file_path, description))
        with self._ctx.http_gateway.open(description['url']) as (final_url, in_stream):
            description['url'] = final_url
            if in_stream.status != 200:
                raise FileDownloadException(f'Bad http status! {file_path}: {in_stream.status}')

            self._ctx.file_system.write_incoming_stream(in_stream, target_path)
