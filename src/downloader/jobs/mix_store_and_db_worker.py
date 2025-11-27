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

from downloader.db_utils import can_skip_db
from downloader.job_system import WorkerResult, JobContext, ProgressReporter
from downloader.jobs.load_local_store_job import local_store_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.reporters import InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorker
from downloader.logger import Logger


class MixStoreAndDbWorker(DownloaderWorker):
    def __init__(self, logger: Logger, installation_report: InstallationReportImpl, worker_context: JobContext, progress_reporter: ProgressReporter) -> None:
        self._logger = logger
        self._installation_report = installation_report
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter

    def job_type_id(self) -> int: return MixStoreAndDbJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: MixStoreAndDbJob) -> WorkerResult:  # type: ignore[override]
        self._logger.bench('MixStoreAndDbWorker Loading database: ', job.db.db_id)

        while self._installation_report.any_in_progress_job_with_tags(_local_store_tags):
            self._logger.bench('MixStoreAndDbWorker waiting for store: ', job.db.db_id)
            self._worker_context.wait_for_other_jobs(0.06)

        self._logger.bench('MixStoreAndDbWorker store received: ', job.db.db_id)
        local_store = job.load_local_store_job.local_store
        if local_store is None:
            return [], Exception('MixStoreAndDbWorker must receive a LoadLocalStoreJob with local_store not null.')

        store = local_store.store_by_id(job.db.db_id)
        read_only_store = store.read_only()
        if not read_only_store.has_base_path():  # @TODO: should remove this from here at some point.
            store.write_only().set_base_path(job.config['base_path'])  # After that, all worker stores will be read-only.

        sig = read_only_store.db_state_signature()
        if can_skip_db(job.config['file_checking'], sig, job.db_hash, job.db_size, job.config['filter']):  # @TODO: Eventually we can remove this check altogether and just rely in the one from the previous step
            self._logger.debug('Skipping db process. No changes detected for: ', job.db.db_id)
            job.skipped = True
            return [], None

        self._logger.bench('MixStoreAndDbWorker done: ', job.db.db_id)
        return [ProcessDbMainJob(
            db=job.db,
            db_hash=job.db_hash,
            db_size=job.db_size,
            ini_description=job.ini_description,
            store=read_only_store,
            config=job.config,
        )], None

_local_store_tags = [local_store_tag]
