# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.job_system import WorkerResult, ProgressReporter
from downloader.jobs.load_local_store_job import LoadLocalStoreJob
from downloader.jobs.worker_context import DownloaderWorker, FailCtx
from downloader.local_repository import LocalRepository
from downloader.logger import Logger


class LoadLocalStoreWorker(DownloaderWorker):
    def __init__(self, logger: Logger, local_repository: LocalRepository, progress_reporter: ProgressReporter, fail_ctx: FailCtx) -> None:
        self._logger = logger
        self._local_repository = local_repository
        self._progress_reporter = progress_reporter
        self._fail_ctx = fail_ctx

    def job_type_id(self) -> int: return LoadLocalStoreJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: LoadLocalStoreJob) -> WorkerResult:  # type: ignore[override]
        self._logger.bench('LoadLocalStoreWorker start.')
        try:
            local_store = self._local_repository.load_store()
        except Exception as e:
            self._fail_ctx.swallow_error(e)
            return [], e

        job.local_store = local_store
        self._logger.bench('LoadLocalStoreWorker done.')
        return [], None
