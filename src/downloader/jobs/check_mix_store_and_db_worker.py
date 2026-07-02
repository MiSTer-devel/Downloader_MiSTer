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

from downloader.db_utils import can_skip_db
from downloader.job_system import JobContext, ProgressReporter, WorkerResult
from downloader.jobs.load_local_store_job import local_store_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.reporters import InstallationReport
from downloader.jobs.worker_context import DownloaderWorker
from downloader.logger import Logger


class CheckMixStoreAndDbWorker(DownloaderWorker):
    def __init__(self, logger: Logger, installation_report: InstallationReport, worker_context: JobContext, progress_reporter: ProgressReporter) -> None:
        self._logger = logger
        self._installation_report = installation_report
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter

    def job_type_id(self) -> int: return MixStoreAndDbJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: MixStoreAndDbJob) -> WorkerResult:  # type: ignore[override]
        self._logger.bench('CheckMixStoreAndDbWorker Loading database: ', job.db.db_id)

        while self._installation_report.any_in_progress_job_with_tags(_local_store_tags):
            self._logger.bench('CheckMixStoreAndDbWorker waiting for store: ', job.db.db_id)
            self._worker_context.wait_for_other_jobs(0.06)

        if job.load_local_store_job.local_store is None:
            self._logger.bench('CheckMixStoreAndDbWorker skipped because store loading failed: ', job.db.db_id)
            return [], None

        figp = _fingerprint_from_full_store(job)
        if figp is not None and can_skip_db(job.config['file_checking'], figp, job.db_hash, job.db_size, job.config['filter']):
            self._logger.debug('Online check: no changes detected for: ', job.db.db_id)
            job.skipped = True

        self._logger.bench('CheckMixStoreAndDbWorker done: ', job.db.db_id)
        return [], None


def _fingerprint_from_full_store(job: MixStoreAndDbJob):
    local_store = job.load_local_store_job.local_store
    if local_store is None:
        return None
    return local_store.unwrap_local_store()['db_fingerprints'].get(job.db.db_id, None)


_local_store_tags = [local_store_tag]
