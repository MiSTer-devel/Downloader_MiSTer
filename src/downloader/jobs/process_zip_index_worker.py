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

from typing import Any, Dict, List, Optional, Tuple

from downloader.db_entity import check_no_url_files, fix_folders, fix_files, fix_zip
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_zip_kind, make_transfer_job
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.jobs.process_db_index_worker import create_fetch_jobs, process_index_job_main_sequence
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

        logger.bench('ProcessZipIndexWorker fix zips, files & folders: ', db.db_id, zip_id)
        fix_folders(summary.folders)  # @TODO: Try to look for a better place to put this, while validating zip_index entity for example which we don't do yet.
        fix_files(summary.files)
        if fix_zip(zip_description):
            job.has_new_zip_summary = True

        non_existing_pkgs, need_update_pkgs, created_folders, zip_data, error = process_index_job_main_sequence(self._ctx, job, summary, store)
        if error is not None:
            return [], error

        job.filtered_data = zip_data[job.zip_id] if job.zip_id in zip_data else {'files': {}, 'folders': {}}

        total_files_size = 0
        for file_pkg in non_existing_pkgs:
            total_files_size += file_pkg.description['size']
        for file_pkg in need_update_pkgs:
            total_files_size += file_pkg.description['size']

        needs_extracting_single_files = 'kind' in zip_description and zip_description['kind'] == 'extract_single_files'
        less_file_count = len(summary.files) < config['zip_file_count_threshold']
        less_accumulated_mbs = total_files_size < (1000 * 1000 * config['zip_accumulated_mb_threshold'])

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            next_jobs = create_fetch_jobs(self._ctx, db.db_id, non_existing_pkgs, need_update_pkgs, created_folders, zip_description.get('base_files_url', db.base_files_url))

        else:
            next_jobs, error = self._make_open_zip_contents_job(job, non_existing_pkgs + need_update_pkgs, store)
            if error is not None:
                return [], error

        self._fill_fragment_with_zip_index(job.result_zip_index, job)
        logger.bench('ProcessZipIndexWorker done: ', db.db_id, zip_id)
        return next_jobs, None

    def _make_open_zip_contents_job(self, job: ProcessZipIndexJob, unzip_file_pkgs: List[PathPackage], store: ReadOnlyStoreAdapter) -> Tuple[List[Job], Optional[Exception]]:
        if len(unzip_file_pkgs) == 0:
            return [], None

        try:
            check_no_url_files(unzip_file_pkgs, job.db.db_id)
        except Exception as e:
            return [], e

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

        data_job = make_transfer_job(job.zip_description['contents_file']['url'], job.zip_description['contents_file'], False, job.db.db_id)
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
            transfer_job=data_job,
            action_text=job.zip_description['description'],
            zip_base_files_url=job.zip_description.get('base_files_url', '').strip(),
            filtered_data=job.filtered_data or {'files': {}, 'folders': {}}
        )
        data_job.after_job = open_zip_contents_job  # type: ignore[union-attr]
        return [data_job], None  # type: ignore[list-item]

    @staticmethod
    def _create_target_package(calculator: TargetPathsCalculator, kind: ZipKind, description: Dict[str, Any]) -> Tuple[Optional[PathPackage], Optional[Exception]]:
        if kind == ZipKind.EXTRACT_ALL_CONTENTS:
            if 'target_folder_path' not in description or not isinstance(description['target_folder_path'], str):
                return None, Exception('extract_all_contents zip requires string "target_folder_path".')
            else:
                return calculator.deduce_target_path(description['target_folder_path'], description, PathType.FOLDER)
        elif kind == ZipKind.EXTRACT_SINGLE_FILES:
            return None, None
        else: raise ValueError(f"Impossible kind '{kind}'")

    def _fill_fragment_with_zip_index(self, fragment: StoreFragmentDrivePaths, job: ProcessZipIndexJob) -> None:
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
            .deduce_target_path(path, job.zip_description, PathType.FOLDER)

        if path_error is not None:
            self._ctx.swallow_error(path_error)

        if path_pkg.pext_props and path_pkg.is_pext_external():
            drive = path_pkg.pext_props.drive
            fragment['external_paths'][drive] = {'files': {}, 'folders': {}}
            for file_path, file_description in job.zip_index.files.items():
                fragment['external_paths'][drive]['files'][file_path[1:] if file_path[0] == '|' else file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['external_paths'][drive]['folders'][folder_path[1:] if folder_path[0] == '|' else folder_path] = folder_description
        elif path_pkg.is_pext_standard():
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path[1:] if file_path[0] == '|' else file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path[1:] if folder_path[0] == '|' else folder_path] = folder_description

        else:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path] = folder_description
