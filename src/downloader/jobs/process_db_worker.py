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

from typing import Dict, Any, Optional
from dataclasses import dataclass

from downloader.db_entity import DbEntity
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_process_zip_job, make_open_zip_index_job, make_zip_tag, ZipJobContext
from downloader.jobs.process_db_zips_waiter_job import ProcessDbZipsWaiterJob
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.index import Index
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.constants import K_USER_DEFINED_OPTIONS, K_FILTER, K_OPTIONS, K_BASE_PATH
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.local_store_wrapper import NO_HASH_IN_STORE_CODE, ReadOnlyStoreAdapter


class ProcessDbWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessDbJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbJob) -> WorkerResult:
        read_only_store = job.store.read_only()
        write_only_store = job.store.write_only()

        self._ctx.logger.debug(f"Building db config '{job.db.db_id}'...")
        config = build_db_config(input_config=self._ctx.config, db=job.db, ini_description=job.ini_description)

        if not read_only_store.has_base_path():
            write_only_store.set_base_path(config[K_BASE_PATH])

        for zip_id in list(read_only_store.zips):
            if zip_id in job.db.zips:
                continue

            write_only_store.remove_zip_id(zip_id)

        if len(job.db.zips) > 0:
            zip_jobs = []
            zip_job_tags = []

            for zip_id, zip_description in job.db.zips.items():
                zip_job = _make_zip_job(ZipJobContext(zip_id=zip_id, zip_description=zip_description, config=config, job=job))
                zip_job_tags.append(make_zip_tag(job.db, zip_id))
                zip_jobs.append(zip_job)

            zip_jobs.append(ProcessDbZipsWaiterJob(
                db=job.db,
                config=config,
                store=job.store,
                ini_description=job.ini_description,
                full_resync=job.full_resync,
                zip_job_tags=zip_job_tags
            ))

            return zip_jobs, None
        else:
            return ProcessIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=config,
                index=Index(files=job.db.files, folders=job.db.folders, base_files_url=job.db.base_files_url),
                store=job.store,
                full_resync=job.full_resync,
            ), None


def build_db_config(input_config: Dict[str, Any], db: DbEntity, ini_description: Dict[str, Any]) -> Dict[str, Any]:
    config = input_config.copy()
    user_defined_options = config[K_USER_DEFINED_OPTIONS]

    for key, option in db.default_options.items():
        if key not in user_defined_options or (key == K_FILTER and '[mister]' in option.lower()):
            config[key] = option

    if K_OPTIONS in ini_description:
        ini_description[K_OPTIONS].apply_to_config(config)

    if config[K_FILTER] is not None and '[mister]' in config[K_FILTER].lower():
        mister_filter = '' if K_FILTER not in config or config[K_FILTER] is None else config[K_FILTER].lower()
        config[K_FILTER] = config[K_FILTER].lower().replace('[mister]', mister_filter).strip()

    return config

def _make_zip_job(z: ZipJobContext) -> Job:
    if 'summary_file' in z.zip_description:
        index = z.job.store.read_only().zip_index(z.zip_id)


        #@TODO ZIP_INDEX method does not pull data from filtered_zip_data so and that makes the current test to not pass

        there_is_a_recent_store_index = index is not None and index['hash'] == z.zip_description['summary_file']['hash'] and index['hash'] != NO_HASH_IN_STORE_CODE
        if there_is_a_recent_store_index:
            job = _make_process_zip_job_from_ctx(z, zip_index=index, has_new_zip_index=False)
        else:
            job, summary_info =  make_open_zip_index_job(z, z.zip_description['summary_file'])

    elif 'internal_summary' in z.zip_description:
        job = _make_process_zip_job_from_ctx(z, zip_index=z.zip_description['internal_summary'], has_new_zip_index=True)
    else:
        raise Exception(f"Unknown zip description for zip '{z.zip_id}' in db '{z.job.db.db_id}'")
        # @TODO: Handle this case, it should never raise in any case

    return job


def _make_process_zip_job_from_ctx(z: ZipJobContext, zip_index: Dict[str, Any], has_new_zip_index: bool):
    return make_process_zip_job(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        zip_index=zip_index,
        config=z.config,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        full_resync=z.job.full_resync,
        has_new_zip_index=has_new_zip_index
    )
