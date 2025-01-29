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
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.job_system import WorkerResult
from typing import Optional


class CopyFileWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return CopyFileJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: CopyFileJob) -> WorkerResult:  # type: ignore[override]
        error = self._copy_file(source=job.source, temp_path=job.temp_path, info=job.info)
        if error is not None:
            return None, error

        return job.after_job, None

    def _copy_file(self, source: str, temp_path: str, info: str) -> Optional[FileCopyError]:
        try:
            if not source.startswith("/"):
                source = self._ctx.file_system.resolve(source)

            self._ctx.file_system.copy(source, temp_path)

            if not self._ctx.file_system.is_file(temp_path, use_cache=False):
                return FileCopyError(f'Missing {info}')
        except BaseException as e:
            return FileCopyError(f'Exception during copy! {info}: {str(e)}')
        else: return None
