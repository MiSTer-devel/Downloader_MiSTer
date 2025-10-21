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

from typing import Dict, Any, Optional, Tuple

from downloader.config import FileChecking
from downloader.db_entity import check_zip, fix_folders, ZipIndexEntity
from downloader.db_utils import build_db_config
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_process_zip_index_job, make_open_zip_summary_job, make_zip_tag, ZipJobContext
from downloader.jobs.wait_db_zips_job import WaitDbZipsJob
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.index import Index
from downloader.jobs.worker_context import DownloaderWorkerBase, NilJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.local_store_wrapper import NO_HASH_IN_STORE_CODE, StoreFragmentZipSummary


class ProcessDbMainWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessDbMainJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbMainJob) -> WorkerResult:  # type: ignore[override]
        self._ctx.logger.bench('ProcessDbMainWorker start: ', job.db.db_id)
        result = self._operate_on_impl(job)
        self._ctx.logger.bench('ProcessDbMainWorker end: ', job.db.db_id)
        return result

    def _operate_on_impl(self, job: ProcessDbMainJob) -> WorkerResult:
        db, config, store, ini_description = job.db, job.config, job.store, job.ini_description

        logger = self._ctx.logger

        read_only_store = store.read_only()

        if db.needs_migration():
            logger.bench('ProcessDbMainWorker migrating db: ', db.db_id)
            error = db.migrate()
            if error is not None:
                return [], error

        fix_folders(db.folders)

        self._ctx.file_download_session_logger.print_header(db)
        logger.bench("ProcessDbMainWorker Building db config: ", db.db_id)
        config = job.config = build_db_config(input_config=self._ctx.config, db=db, ini_description=ini_description)

        sig = read_only_store.db_state_signature()
        if config['file_checking'] == FileChecking.ON_DB_CHANGES \
            and sig['hash'] == job.db_hash \
            and sig['size'] == job.db_size \
            and sig['timestamp'] == db.timestamp \
            and sig['filter'] == config['filter']:
                self._ctx.logger.debug('Skipping db process. No changes detected for: ', db.db_id)
                return [], None  # @TODO: Cover this scenario in tests

        if not read_only_store.has_base_path():  # @TODO: should remove this from here at some point.
            store.write_only().set_base_path(config['base_path'])  # After that, all worker stores will be read-only.

        for zip_id in list(read_only_store.zips):
            if zip_id in db.zips:
                continue

            job.removed_zips.append(zip_id)

        if len(db.zips) > 0:
            zip_jobs = []
            zip_job_tags = []

            logger.bench('ProcessDbMainWorker ZIP summaries calc: ', db.db_id)
            zip_summaries = read_only_store.zip_summaries()

            logger.bench('ProcessDbMainWorker ZIP make jobs: ', db.db_id)
            for zip_id, zip_description in db.zips.items():
                #if zip_id != 'cheats_folder_psx': continue
                zip_job, err = _make_zip_job(zip_summaries.get(zip_id, None), ZipJobContext(zip_id=zip_id, zip_description=zip_description, config=config, job=job))
                if err is not None:
                    self._ctx.swallow_error(err)
                    job.ignored_zips.append(zip_id)
                    continue

                zip_job_tags.append(make_zip_tag(db, zip_id))
                zip_jobs.append(zip_job)

            waiter_job = WaitDbZipsJob(
                db=db,
                config=config,
                store=store,
                ini_description=ini_description,
                zip_job_tags=zip_job_tags
            )

            next_jobs = [*zip_jobs, waiter_job]
        else:
            index_job = ProcessDbIndexJob(
                db=db,
                ini_description=ini_description,
                config=config,
                index=Index(files=db.files, folders=db.folders),
                store=store,
            )
            next_jobs = [index_job]

        return next_jobs, None


def _make_zip_job(stored_index: Optional[StoreFragmentZipSummary], z: ZipJobContext) -> Tuple[Job, Optional[Exception]]:
    try:
        check_zip(z.zip_description, z.job.db.db_id, z.zip_id)
    except Exception as e:
        return NilJob(), e

    if 'summary_file' in z.zip_description:
        def _make_it_from_store(): return _make_process_zip_job_from_ctx(z, zip_summary=stored_index, has_new_zip_summary=False)

        if stored_index is None:
            job = make_open_zip_summary_job(z, z.zip_description['summary_file'], None)
        elif stored_index['hash'] == z.zip_description['summary_file']['hash'] and stored_index['hash'] != NO_HASH_IN_STORE_CODE:
            job = _make_it_from_store()
        else:
            job = make_open_zip_summary_job(z, z.zip_description['summary_file'], _make_it_from_store())

    else:
        zip_summary = z.zip_description['internal_summary']  # This is already validated in check_zip
        job = _make_process_zip_job_from_ctx(z, zip_summary=zip_summary, has_new_zip_summary=True)

    return job, None


def _make_process_zip_job_from_ctx(z: ZipJobContext, zip_summary: Dict[str, Any], has_new_zip_summary: bool):
    base_files_url = z.job.db.base_files_url
    if 'base_files_url' in z.zip_description:
        base_files_url = z.zip_description['base_files_url']

    zip_index = ZipIndexEntity(
        files=zip_summary['files'],
        folders=zip_summary['folders'],
        base_files_url=zip_summary.get('base_files_url', base_files_url),
        version=z.job.db.version
    )

    return make_process_zip_index_job(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        zip_index=zip_index,
        config=z.config,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        has_new_zip_summary=has_new_zip_summary
    )
