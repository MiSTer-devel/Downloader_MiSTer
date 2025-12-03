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

from threading import Lock

from downloader.config import Config
from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE
from downloader.db_entity import DbEntity
from downloader.db_utils import build_db_config, can_skip_db
from downloader.file_system import FileSystem
from downloader.job_system import WorkerResult, JobContext, ProgressReporter
from downloader.jobs.load_local_store_sigs_job import local_store_sigs_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.reporters import InstallationReportImpl, FileDownloadSessionLogger
from downloader.jobs.worker_context import DownloaderWorker, FailCtx
from downloader.logger import Logger


class OpenDbWorker(DownloaderWorker):
    def __init__(self, file_system: FileSystem, logger: Logger, file_download_session_logger: FileDownloadSessionLogger, installation_report: InstallationReportImpl, worker_context: JobContext, progress_reporter: ProgressReporter, fail_ctx: FailCtx, config: Config) -> None:
        self._file_system = file_system
        self._logger = logger
        self._file_download_session_logger = file_download_session_logger
        self._installation_report = installation_report
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter
        self._fail_ctx = fail_ctx
        self._config = config
        self._lock = Lock()
        self._returned_load_local_store_job = False

    def job_type_id(self) -> int: return OpenDbJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: OpenDbJob) -> WorkerResult:  # type: ignore[override]
        self._logger.bench('OpenDbWorker Loading database: ', job.section)

        # @TODO: Skip db before opening it, need to calculate the filter in other way for that and that's it. Around 300ms savings

        try:
            db_props = self._file_system.load_dict_from_transfer(job.transfer_job.source, job.transfer_job.transfer())
        except Exception as e:
            self._fail_ctx.swallow_error(e)
            return [], e

        self._logger.bench('OpenDbWorker Validating database: ', job.section)
        try:
            db = DbEntity(db_props, job.section)
        except Exception as e:
            self._fail_ctx.swallow_error(e)
            return [], e

        self._logger.bench('OpenDbWorker database opened: ', job.section)

        if db.needs_migration():
            self._logger.bench('OpenDbWorker migrating db: ', db.db_id)
            error = db.migrate()
            if error is not None:
                self._fail_ctx.swallow_error(error)
                return [], error

        self._file_download_session_logger.print_header(db)

        calcs = job.transfer_job.calcs  # type: ignore[union-attr]
        if calcs is None:
            self._fail_ctx.swallow_error(Exception(f'OpenDbWorker [{db.db_id}] must receive a transfer_job with calcs not null.'))
            calcs = {}

        db_hash = calcs.get('hash', DB_STATE_SIGNATURE_NO_HASH)
        db_size = calcs.get('size', DB_STATE_SIGNATURE_NO_SIZE)

        while self._installation_report.any_in_progress_job_with_tags(_local_store_sigs_tags):
            self._logger.bench('OpenDbWorker waiting for store sigs: ', job.section)
            self._worker_context.wait_for_other_jobs(0.06)

        ini_description = job.ini_description

        self._logger.bench("OpenDbWorker Building db config: ", db.db_id)
        config = build_db_config(input_config=self._config, db=db, ini_description=ini_description)

        sigs = job.load_local_store_sigs_job.local_store_sigs
        if sigs is not None:
            sig = sigs.get(job.section, None)
            if sig is not None:
                if can_skip_db(self._config['file_checking'], sig, db_hash, db_size, config['filter']):
                    self._logger.debug('Skipping db process. No changes detected for: ', db.db_id)
                    job.skipped = True
                    return [], None

        jobs = []
        if not job.load_local_store_job.local_store and not self._returned_load_local_store_job:
            with self._lock:
                if not self._returned_load_local_store_job:
                    self._returned_load_local_store_job = True
                    jobs.append(job.load_local_store_job)

        jobs.append(MixStoreAndDbJob(
            db=db,
            db_hash=db_hash,
            db_size=db_size,
            ini_description=ini_description,
            config=config,
            load_local_store_job=job.load_local_store_job
        ))

        self._logger.bench('OpenDbWorker done: ', job.section)
        return jobs, None


_local_store_sigs_tags = [local_store_sigs_tag]
