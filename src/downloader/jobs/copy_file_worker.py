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
from downloader.jobs.errors import FileCopyError
from downloader.jobs.worker_context import DownloaderWorker
from typing import Optional


class CopyFileWorker(DownloaderWorker):
    def job_type_id(self) -> int: return CopyFileJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: CopyFileJob) -> Optional[FileCopyError]:
        error = self._copy_file(source=job.source, temp_path=job.temp_path, info=job.info)
        if error is not None:
            return error

        if job.after_job is not None:
            self._ctx.job_ctx.push_job(job.after_job)

    def _copy_file(self, source: str, temp_path: str, info: str) -> Optional[FileCopyError]:
        try:
            if not source.startswith("/"):
                source = self._ctx.file_system.resolve(source)

            self._ctx.file_system.copy(source, temp_path)

            if not self._ctx.file_system.is_file(temp_path, use_cache=False):
                return FileCopyError(f'Missing {info}')
        except BaseException as e:
            return FileCopyError(f'Exception during copy! {info}: {str(e)}')
