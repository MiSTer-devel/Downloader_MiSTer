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

from typing import Dict, Any, Set
from dataclasses import dataclass
import threading

from downloader.db_entity import DbEntity
from downloader.jobs.jobs_factory import make_get_zip_file_jobs, make_process_zip_job
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.index import Index
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.constants import K_USER_DEFINED_OPTIONS, K_FILTER, K_OPTIONS
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.local_store_wrapper import NO_HASH_IN_STORE_CODE


class ProcessDbWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = threading.Lock()
        self._full_partitions: Set[str] = set()

    def initialize(self): self._ctx.job_system.register_worker(ProcessDbJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ProcessDbJob):
        config = self._build_db_config(input_config=self._ctx.config, db=job.db, ini_description=job.ini_description)

        for zip_id, zip_description in job.db.zips.items():
            self._ctx.zip_barrier_lock.require_zip(job.db.db_id, zip_id)
            self._push_zip_jobs(_ZipCtx(zip_id=zip_id, zip_description=zip_description, config=config, job=job))

        for zip_id, zip_description in job.store.read_only().zips.items():
            if zip_id in job.db.zips:
                continue

            print(zip_id)

        while not self._ctx.zip_barrier_lock.is_barrier_free(job.db.db_id):
            self._ctx.job_system.wait_for_other_jobs()

        self._ctx.job_system.push_job(ProcessIndexJob(
            db=job.db,
            ini_description=job.ini_description,
            config=config,
            index=Index(files=job.db.files, folders=job.db.folders, base_files_url=job.db.base_files_url),
            store=job.store,
            full_resync=job.full_resync,
        ))

    def _build_db_config(self, input_config: Dict[str, Any], db: DbEntity, ini_description: Dict[str, Any]) -> Dict[str, Any]:
        self._ctx.logger.debug(f"Building db config '{db.db_id}'...")

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

    def _push_zip_jobs(self, z: '_ZipCtx'):
        if 'summary_file' in z.zip_description:
            index = z.job.store.read_only().zip_index(z.zip_id)
            there_is_a_recent_store_index = index is not None and index['hash'] == z.zip_description['summary_file']['hash'] and index['hash'] != NO_HASH_IN_STORE_CODE
            if there_is_a_recent_store_index:
                self._push_process_zip_job(z, zip_index=index, has_new_zip_index=False)
            else:
                self._push_get_zip_index_and_open_jobs(z, z.zip_description['summary_file'])

        elif 'internal_summary' in z.zip_description:
            self._push_process_zip_job(z, zip_index=z.zip_description['internal_summary'], has_new_zip_index=True)
        else:
            raise Exception(f"Unknown zip description for zip '{z.zip_id}' in db '{z.job.db.db_id}'")
            # @TODO: Handle this case

    def _push_process_zip_job(self, z: '_ZipCtx', zip_index: Dict[str, Any], has_new_zip_index: bool):
        self._ctx.job_system.push_job(make_process_zip_job(
            zip_id=z.zip_id,
            zip_description=z.zip_description,
            zip_index=zip_index,
            config=z.config,
            db=z.job.db,
            ini_description=z.job.ini_description,
            store=z.job.store,
            full_resync=z.job.full_resync,
            has_new_zip_index=has_new_zip_index
        ))

    def _push_get_zip_index_and_open_jobs(self, z: '_ZipCtx', file_description: Dict[str, Any]):
        get_file_job, validate_job = make_get_zip_file_jobs(db=z.job.db, zip_id=z.zip_id, description=file_description)
        validate_job.after_job = OpenZipIndexJob(
            zip_id=z.zip_id,
            zip_description=z.zip_description,
            db=z.job.db,
            ini_description=z.job.ini_description,
            store=z.job.store,
            full_resync=z.job.full_resync,
            download_path=validate_job.target_file_path,
            config=z.config,
            get_file_job=get_file_job
        )
        self._ctx.job_system.push_job(get_file_job)


@dataclass
class _ZipCtx:
    zip_id: str
    zip_description: Dict[str, Any]
    config: Dict[str, Any]
    job: ProcessDbJob
