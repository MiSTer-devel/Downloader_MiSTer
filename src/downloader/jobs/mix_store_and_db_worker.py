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

from typing import Any, Mapping, Optional, cast

from downloader.db_utils import can_skip_db, can_skip_db_with_external_store_fingerprints
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.external_store_fingerprints import expected_external_store_fingerprints, has_external_store_fingerprint_metadata
from downloader.local_store_wrapper import DbStateFingerprint, ReadOnlyStoreAdapter
from downloader.job_system import WorkerResult, JobContext, ProgressReporter
from downloader.jobs.load_local_store_job import local_store_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.reporters import InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorker
from downloader.logger import Logger


class MixStoreAndDbWorker(DownloaderWorker):
    def __init__(self, logger: Logger, installation_report: InstallationReportImpl, worker_context: JobContext, progress_reporter: ProgressReporter, external_drives_repository: ExternalDrivesRepository) -> None:
        self._logger = logger
        self._installation_report = installation_report
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter
        self._external_drives_repository = external_drives_repository

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

        figp = read_only_store.db_state_fingerprint()
        if can_skip_db_after_store_load(job, figp, read_only_store, self._external_drives_repository):
            if job.fingerprint_metadata_required and has_expected_external_store_fingerprints(figp):
                self._logger.debug('Forcing store save to rebuild external fingerprint artifacts for: ', job.db.db_id)
                local_store.mark_force_save()
            self._logger.debug('Skipping db process. No changes detected for: ', job.db.db_id)
            job.skipped = True
            return [], None

        if job.fingerprint_metadata_required and not has_external_store_fingerprint_metadata(figp):
            # Processing was forced only to establish the external store fingerprints metadata,
            # which is stamped at save time: the run may otherwise produce no store changes, so
            # guarantee the save now or the store never converges and reprocesses every run.
            self._logger.debug('Forcing store save to stamp missing external fingerprint metadata for: ', job.db.db_id)
            local_store.mark_force_save()

        self._logger.bench('MixStoreAndDbWorker done: ', job.db.db_id)
        return [ProcessDbMainJob(
            db=job.db,
            db_hash=job.db_hash,
            db_size=job.db_size,
            ini_description=job.ini_description,
            store=read_only_store,
            config=job.config,
        )], None

def can_skip_db_after_store_load(
        job: MixStoreAndDbJob,
        figp: Mapping[str, Any],
        read_only_store: ReadOnlyStoreAdapter,
        external_drives_repository: Optional[ExternalDrivesRepository],
) -> bool:
    if has_external_store_fingerprint_metadata(figp):
        return can_skip_db_with_external_store_fingerprints(
            job.config['file_checking'],
            figp,
            job.db_hash,
            job.db_size,
            job.config['filter'],
            read_only_store.external_fragment_fingerprints(),
        )

    if job.fingerprint_metadata_required:
        return False

    if not can_skip_db(job.config['file_checking'], cast(DbStateFingerprint, figp), job.db_hash, job.db_size, job.config['filter']):
        return False

    if external_drives_repository is None:
        return True

    return all_store_drives_connected(read_only_store, external_drives_repository)

def all_store_drives_connected(read_only_store: ReadOnlyStoreAdapter, external_drives_repository: ExternalDrivesRepository) -> bool:
    # A store referencing a disconnected external drive cannot be trusted by fingerprint
    # alone: from this run's point of view the files on that drive are gone, so the db
    # must be processed to reinstall or relocate them.
    if not read_only_store.has_externals:
        return True
    connected_drives = external_drives_repository.connected_drives()
    return all(drive in connected_drives for drive in read_only_store.external_drives)

def has_expected_external_store_fingerprints(figp: Mapping[str, Any]) -> bool:
    external_store_fingerprints = expected_external_store_fingerprints(figp)
    return external_store_fingerprints is not None and len(external_store_fingerprints) > 0

_local_store_tags = [local_store_tag]
