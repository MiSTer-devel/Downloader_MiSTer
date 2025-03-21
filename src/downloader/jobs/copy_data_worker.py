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

import hashlib
from downloader.job_system import WorkerResult
from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext


class CopyDataWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext) -> None:
        self._ctx = ctx

    def job_type_id(self) -> int: return CopyDataJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: CopyDataJob) -> WorkerResult:  # type: ignore[override]
        buf = self._ctx.file_system.read_file_bytes(job.source if job.source.startswith('/') else self._ctx.file_system.resolve(job.source))
        buf.seek(0)
        if job.calcs is not None:
            job.calcs['hash'] = hashlib.md5(buf.read()).hexdigest()
            job.calcs['size'] = buf.getbuffer().nbytes
        buf.seek(0)
        job.data = buf
        return [] if job.after_job is None else [job.after_job], None
