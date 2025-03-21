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

from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE
from downloader.db_entity import DbEntity
from downloader.job_system import WorkerResult
from downloader.jobs.load_local_store_job import local_store_tag
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.worker_context import DownloaderWorkerBase


class OpenDbWorker(DownloaderWorkerBase):
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

        calcs = job.transfer_job.calcs  # type: ignore[union-attr]
        if calcs is None:
            self._ctx.swallow_error(Exception(f'OpenDbWorker [{db.db_id}] must receive a transfer_job with calcs not null.'))
            calcs = {}

        while self._ctx.installation_report.any_in_progress_job_with_tags(_local_store_tags):
            self._ctx.logger.bench('OpenDbWorker waiting for store: ', job.section)
            self._ctx.job_ctx.wait_for_other_jobs(0.06)

        self._ctx.logger.bench('OpenDbWorker store received: ', job.section)
        local_store, full_resync = job.load_local_store_job.local_store, job.load_local_store_job.full_resync
        if local_store is None:
            return [], Exception('OpenDbWorker must receive a LoadLocalStoreJob with local_store not null.')

        store = local_store.store_by_id(job.section)
        ini_description = job.ini_description

        self._ctx.logger.bench('OpenDbWorker done: ', job.section)
        return [ProcessDbMainJob(
            db=db,
            db_hash=calcs.get('hash', DB_STATE_SIGNATURE_NO_HASH),
            db_size=calcs.get('size', DB_STATE_SIGNATURE_NO_SIZE),
            ini_description=ini_description,
            store=store,
            full_resync=full_resync
        )], None

    def _open_db(self, section: str, source: str, transfer: Any, /) -> DbEntity:
        db_props = self._ctx.file_system.load_dict_from_transfer(source, transfer)
        self._ctx.logger.bench('OpenDbWorker Validating database: ', section)
        db_entity = DbEntity(db_props, section)
        return db_entity


_local_store_tags = [local_store_tag]
