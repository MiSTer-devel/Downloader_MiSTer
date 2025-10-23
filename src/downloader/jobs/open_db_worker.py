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

from typing import Any
from threading import Lock

from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE
from downloader.db_entity import DbEntity
from downloader.db_utils import build_db_config, can_skip_db
from downloader.job_system import WorkerResult
from downloader.jobs.load_local_store_sigs_job import local_store_sigs_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext


class OpenDbWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = Lock()
        self._returned_load_local_store_job = False

    def job_type_id(self) -> int: return OpenDbJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenDbJob) -> WorkerResult:  # type: ignore[override]
        self._ctx.logger.bench('OpenDbWorker Loading database: ', job.section)
        try:
            db = self._open_db(job.section, job.transfer_job.source, job.transfer_job.transfer())  # type: ignore[union-attr]
        except Exception as e:
            self._ctx.swallow_error(e)
            return [], e

        self._ctx.logger.bench('OpenDbWorker database opened: ', job.section)

        self._ctx.file_download_session_logger.print_header(db)

        calcs = job.transfer_job.calcs  # type: ignore[union-attr]
        if calcs is None:
            self._ctx.swallow_error(Exception(f'OpenDbWorker [{db.db_id}] must receive a transfer_job with calcs not null.'))
            calcs = {}

        db_hash = calcs.get('hash', DB_STATE_SIGNATURE_NO_HASH)
        db_size = calcs.get('size', DB_STATE_SIGNATURE_NO_SIZE)

        while self._ctx.installation_report.any_in_progress_job_with_tags(_local_store_sigs_tags):
            self._ctx.logger.bench('OpenDbWorker waiting for store sigs: ', job.section)
            self._ctx.job_ctx.wait_for_other_jobs(0.06)

        ini_description = job.ini_description

        self._ctx.logger.bench("OpenDbWorker Building db config: ", db.db_id)
        config = build_db_config(input_config=self._ctx.config, db=db, ini_description=ini_description)

        sigs = job.load_local_store_sigs_job.local_store_sigs
        if sigs is not None:
            sig = sigs.get(job.section, None)
            if sig is not None:
                if can_skip_db(config, sig, db_hash, db_size, db):
                    self._ctx.logger.debug('Skipping db process. No changes detected for: ', db.db_id)
                    job.skipped = True
                    return [], None

        jobs = []
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

        self._ctx.logger.bench('OpenDbWorker done: ', job.section)
        return jobs, None

    def _open_db(self, section: str, source: str, transfer: Any, /) -> DbEntity:
        db_props = self._ctx.file_system.load_dict_from_transfer(source, transfer)
        self._ctx.logger.bench('OpenDbWorker Validating database: ', section)
        db_entity = DbEntity(db_props, section)
        return db_entity


_local_store_sigs_tags = [local_store_sigs_tag]
