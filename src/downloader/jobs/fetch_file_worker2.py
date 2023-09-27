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

from downloader.constants import K_DOWNLOADER_TIMEOUT
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadException


class FetchFileWorker2(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(FetchFileJob2.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: FetchFileJob2):
        url, download_path, info = job.url, job.download_path, job.info
        self._fetch_file(url, download_path, info)
        if job.after_job is not None: self._ctx.job_system.push_job(job.after_job)

    def _fetch_file(self, url: str, download_path: str, info: str):
        with self._ctx.http_gateway.open(url) as (final_url, in_stream):
            if in_stream.status != 200:
                raise FileDownloadException(f'Bad http status! {info}: {in_stream.status}')

            self._ctx.file_system.write_incoming_stream(in_stream, download_path, timeout=self._ctx.config[K_DOWNLOADER_TIMEOUT])

        if not self._ctx.file_system.is_file(download_path, use_cache=False):
            raise FileDownloadException(f'Missing {info}')
