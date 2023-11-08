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

from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.errors import FileCopyException
from downloader.jobs.worker_context import DownloaderWorker


class CopyFileWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(CopyFileJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: CopyFileJob):
        source, temp_path, info = job.source, job.temp_path, job.info
        self._copy_file(source, temp_path, info)
        if job.after_job is not None: self._ctx.job_system.push_job(job.after_job)

    def _copy_file(self, source: str, temp_path: str, info: str):
        if not source.startswith("/"):
            source = self._ctx.file_system.resolve(source)

        self._ctx.file_system.copy(source, temp_path)

        if not self._ctx.file_system.is_file(temp_path, use_cache=False):
            raise FileCopyException(f'Missing {info}')
