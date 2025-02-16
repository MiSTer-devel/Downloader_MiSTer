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

from typing import Any, Dict, List, Optional, Tuple

from downloader.db_entity import fix_folders
from downloader.file_filter import ZipData
from downloader.file_system import FileWriteError, FolderCreationError
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_get_zip_file_jobs, make_zip_kind
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.process_db_index_worker import create_fetch_jobs, create_packages_from_index, process_check_file_packages, process_create_folder_packages, process_validate_packages, try_reserve_space
from downloader.local_store_wrapper import ReadOnlyStoreAdapter, StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.target_path_calculator import TargetPathsCalculator


class ProcessZipIndexWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessZipIndexJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessZipIndexJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        zip_id, zip_description, db, config, summary, full_resync = job.zip_id, job.zip_description, job.db, job.config, job.zip_index, job.full_resync

        logger.bench('ProcessZipIndexWorker start: ', db.db_id, zip_id)
        store = job.store.select(job.zip_index).read_only()
        fix_folders(summary.folders)  # @TODO: Try to look for a better place to put this, while validating zip_index entity for example which we don't do yet.

        logger.bench('ProcessZipIndexWorker create pkgs: ', db.db_id, zip_id)
        check_file_pkgs, job.files_to_remove, create_folder_pkgs, job.directories_to_remove, zip_data = create_packages_from_index(self._ctx, config, summary, db, store, zip_id is not None)

        logger.bench('ProcessZipIndexWorker Precaching is_file: ', db.db_id, zip_id)
        self._ctx.file_system.precache_is_file_with_folders(create_folder_pkgs)

        logger.bench('ProcessZipIndexWorker check pkgs: ', db.db_id, zip_id, len(check_file_pkgs))
        unzip_file_pkgs, validate_pkgs, job.present_not_validated_files = process_check_file_packages(self._ctx, check_file_pkgs, db.db_id, store, full_resync)

        logger.bench('ProcessZipIndexWorker validate pkgs: ', db.db_id, zip_id)
        job.present_validated_files, job.skipped_updated_files, more_unzip_file_pkgs = process_validate_packages(self._ctx, validate_pkgs)
        unzip_file_pkgs.extend(more_unzip_file_pkgs)

        logger.bench('ProcessZipIndexWorker Reserve space: ', db.db_id, zip_id)
        job.full_partitions = try_reserve_space(self._ctx, unzip_file_pkgs)
        if len(job.full_partitions) > 0:
            job.failed_files_no_space = unzip_file_pkgs
            logger.debug("Not enough space '%s'!", db.db_id)
            return [], FileWriteError(f"Could not allocate space for {len(unzip_file_pkgs)} files.")

        logger.bench('ProcessZipIndexWorker Create folders: ', db.db_id, zip_id)
        job.removed_folders, job.installed_folders, job.failed_folders = process_create_folder_packages(self._ctx, create_folder_pkgs, db.db_id, summary.folders, store)
        if len(job.failed_folders) > 0:
            return [], FolderCreationError(f"Could not create {len(job.failed_folders)} folders.")

        job.filtered_data = zip_data[job.zip_id] if job.zip_id in zip_data else {'files': {}, 'folders': {}}

        total_files_size = 0
        for file_pkg in unzip_file_pkgs:
            total_files_size += file_pkg.description['size']

        needs_extracting_single_files = 'kind' in zip_description and zip_description['kind'] == 'extract_single_files'
        less_file_count = len(summary.files) < config['zip_file_count_threshold']
        less_accumulated_mbs = total_files_size < (1000 * 1000 * config['zip_accumulated_mb_threshold'])

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            next_jobs = create_fetch_jobs(self._ctx, db.db_id, unzip_file_pkgs, zip_description.get('base_files_url', db.base_files_url))

        else:
            next_jobs, error = self._make_open_zip_contents_job(job, unzip_file_pkgs, store)
            if error is not None:
                return [], error

        self._fill_fragment_with_zip_index(job.result_zip_index, job)
        logger.bench('ProcessZipIndexWorker done: ', db.db_id, zip_id)
        return next_jobs, None

    def _make_open_zip_contents_job(self, job: ProcessZipIndexJob, unzip_file_pkgs: List[PathPackage], store: ReadOnlyStoreAdapter) -> Tuple[List[Job], Optional[Exception]]:
        if len(unzip_file_pkgs) == 0:
            return [], None

        zip_kind, kind_err = make_zip_kind(job.zip_description.get('kind', None), (job.zip_id, job.db.db_id))
        if kind_err is not None:
            self._ctx.swallow_error(kind_err)
            return [], None

        total_amount_of_files_in_zip = len(job.zip_index.files)

        calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)

        target_pkg, target_error = self._create_target_package(calculator, zip_kind, job.zip_description)
        if target_error is not None:
            self._ctx.swallow_error(target_error)
            return [], target_error

        get_file_job, validate_job = make_get_zip_file_jobs(db=job.db, zip_id=job.zip_id, description=job.zip_description['contents_file'], tag=None)
        open_zip_contents_job = OpenZipContentsJob(
            db=job.db,
            store=store,
            ini_description=job.ini_description,
            config=job.config,
            full_resync=job.full_resync,

            zip_id=job.zip_id,
            zip_kind=zip_kind,
            zip_description=job.zip_description,
            target_folder=target_pkg,
            total_amount_of_files_in_zip=total_amount_of_files_in_zip,
            files_to_unzip=unzip_file_pkgs,
            recipient_folders=job.installed_folders,
            contents_zip_temp_path=validate_job.target_file_path,
            action_text=job.zip_description['description'],
            zip_base_files_url=job.zip_description.get('base_files_url', '').strip(),
            filtered_data=job.filtered_data,

            get_file_job=get_file_job,
        )
        open_zip_contents_job.add_tag(job.db.db_id)
        validate_job.after_job = open_zip_contents_job
        return [get_file_job], None

    def _create_target_package(self, calculator: TargetPathsCalculator, kind: ZipKind, description: Dict[str, Any]) -> Tuple[Optional[str], Optional[Exception]]:
        if kind == ZipKind.EXTRACT_ALL_CONTENTS:
            if 'target_folder_path' not in description or not isinstance(description['target_folder_path'], str):
                return None, Exception('extract_all_contents zip requires string "target_folder_path".')
            else:
                return calculator.deduce_target_path(description['target_folder_path'], {}, PathType.FOLDER)
        elif kind == ZipKind.EXTRACT_SINGLE_FILES:
            return None, None
        else: raise ValueError(f"Impossible kind '{kind}'")

    def _fill_fragment_with_zip_index(self, fragment: StoreFragmentDrivePaths, job: ProcessZipIndexJob):
        path = None
        if 'target_folder_path' in job.zip_description:
            path = job.zip_description['target_folder_path']
        elif 'path' in job.zip_description:
            path = job.zip_description['path']
        elif 'internal_summary' in job.zip_description:
            for file_path in job.zip_description['internal_summary']['files']:
                path = file_path
                break
            for folder_path in job.zip_description['internal_summary']['folders']:
                path = folder_path
                break
        else:
            for file_path in job.zip_index.files:
                path = file_path
                break

            for folder_path in job.zip_index.folders:
                path = folder_path
                break

        if path is None:
            return

        path_pkg, path_error = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)\
            .deduce_target_path(path, {}, PathType.FOLDER)

        if path_error is not None:
            self._ctx.swallow_error(path_error)

        if path_pkg.pext_props and path_pkg.is_pext_external():
            drive = path_pkg.pext_props.drive
            fragment['external_paths'][drive] = {'files': {}, 'folders': {}}
            for file_path, file_description in job.zip_index.files.items():
                fragment['external_paths'][drive]['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['external_paths'][drive]['folders'][folder_path[1:]] = folder_description
        elif path_pkg.is_pext_standard():
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path[1:]] = folder_description

        else:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path] = folder_description
