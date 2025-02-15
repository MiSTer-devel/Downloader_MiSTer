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

from typing import Dict, Any, Optional, Tuple

from downloader.db_entity import make_db_tag
from downloader.db_utils import build_db_config
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_process_zip_job, make_open_zip_summary_job, make_zip_tag, ZipJobContext
from downloader.jobs.wait_db_zips_job import WaitDbZipsJob
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.index import Index
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.local_store_wrapper import NO_HASH_IN_STORE_CODE


class ProcessDbMainWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessDbMainJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbMainJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        logger.bench('ProcessDbMainWorker start: ', job.db.db_id)
    
        read_only_store = job.store.read_only()

        self._ctx.file_download_session_logger.print_header(job.db)
        logger.debug("Building db config '%s'...", job.db.db_id)
        config = build_db_config(input_config=self._ctx.config, db=job.db, ini_description=job.ini_description)

        if not read_only_store.has_base_path():  # @TODO: should remove this from here at some point.
            job.store.write_only().set_base_path(config['base_path'])  # After that, all worker stores will be read-only.

        for zip_id in list(read_only_store.zips):
            if zip_id in job.db.zips:
                continue

            job.removed_zips.append(zip_id)

        if len(job.db.zips) > 0:
            zip_jobs = []
            zip_job_tags = []

            for zip_id, zip_description in job.db.zips.items():
                zip_job, err = _make_zip_job(ZipJobContext(zip_id=zip_id, zip_description=zip_description, config=config, job=job))
                if err is not None:
                    self._ctx.swallow_error(err)
                    job.ignored_zips.append(zip_id)
                    continue

                zip_job_tags.append(make_zip_tag(job.db, zip_id))
                zip_jobs.append(zip_job)

            waiter_job = WaitDbZipsJob(
                db=job.db,
                config=config,
                store=job.store,
                ini_description=job.ini_description,
                full_resync=job.full_resync,
                zip_job_tags=zip_job_tags
            )

            next_jobs = [*zip_jobs, waiter_job]
        else:
            index_job = ProcessDbIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=config,
                index=Index(files=job.db.files, folders=job.db.folders, base_files_url=job.db.base_files_url),
                store=job.store,
                full_resync=job.full_resync,
            )
            index_job.add_tag(make_db_tag(job.db.db_id))
            next_jobs = [index_job]

        logger.bench('ProcessDbMainWorker end: ', job.db.db_id)

        return next_jobs, None


def _make_zip_job(z: ZipJobContext) -> Tuple[Job, Optional[Exception]]:
    if 'summary_file' in z.zip_description:
        index = z.job.store.read_only().zip_summary(z.zip_id)

        process_zip_job = None if index is None else _make_process_zip_job_from_ctx(z, zip_summary=index, has_new_zip_summary=False)

        # if there is a recent enough index in the store, use it
        if process_zip_job is not None and index['hash'] == z.zip_description['summary_file']['hash'] and index['hash'] != NO_HASH_IN_STORE_CODE:
            job = process_zip_job
        else:
            job = make_open_zip_summary_job(z, z.zip_description['summary_file'], process_zip_job)

    elif 'internal_summary' in z.zip_description:
        job = _make_process_zip_job_from_ctx(z, zip_summary=z.zip_description['internal_summary'], has_new_zip_summary=True)
    else:
        return z.job, Exception(f"Unknown zip description for zip '{z.zip_id}' in db '{z.job.db.db_id}'")
        # @TODO: Set a more descriptive exception type here, is a exception validation error

    return job, None


def _make_process_zip_job_from_ctx(z: ZipJobContext, zip_summary: Dict[str, Any], has_new_zip_summary: bool):
    return make_process_zip_job(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        zip_summary=zip_summary,
        config=z.config,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        full_resync=z.job.full_resync,
        has_new_zip_summary=has_new_zip_summary
    )
