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

from downloader.job_system import Job, JobSystem, WorkerResult
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext


class AbortJob(Job): type_id: int = JobSystem.get_job_type_id()

class AbortWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext) -> None:
        self._ctx = ctx

    def job_type_id(self) -> int: return AbortJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: Job) -> WorkerResult:
        self._ctx.job_ctx.cancel_pending_jobs()
        return [], None
