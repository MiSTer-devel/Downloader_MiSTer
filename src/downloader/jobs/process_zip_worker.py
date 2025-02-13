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

from downloader.file_system import FileWriteError, FolderCreationError
from downloader.free_space_reservation import Partition
from downloader.job_system import WorkerResult, Job
from downloader.jobs.index import Index
from downloader.jobs.jobs_factory import make_get_zip_file_jobs, make_zip_kind
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.process_index_worker import process_create_folder_packages
from downloader.local_store_wrapper import ReadOnlyStoreAdapter, StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.target_path_calculator import TargetPathsCalculator


class ProcessZipWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessZipJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessZipJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        logger.bench('ProcessZipWorker start.')
        total_files_size = 0
        for file_description in job.zip_index.files.values():
            total_files_size += file_description['size']

        needs_extracting_single_files = 'kind' in job.zip_description and job.zip_description['kind'] == 'extract_single_files'
        less_file_count = len(job.zip_index.files) < job.config['zip_file_count_threshold']
        less_accumulated_mbs = total_files_size < (1000 * 1000 * job.config['zip_accumulated_mb_threshold'])

        process_index_job = None
        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            process_index_job = _make_process_index_job(job)

        if process_index_job is None:
            next_jobs, error = self._make_open_zip_contents_job(job)
            if error is not None:
                return [], error
        else:
            next_jobs = [process_index_job]

        self._fill_fragment_with_zip_index(job.result_zip_index, job)
        logger.bench('ProcessZipWorker done.')
        return next_jobs, None

    def _make_open_zip_contents_job(self, job: ProcessZipJob) -> Tuple[Job, Optional[Exception]]:
        logger = self._ctx.logger
        store = job.store.read_only()

        zip_kind, kind_err = make_zip_kind(job.zip_description.get('kind', None), (job.zip_id, job.db.db_id))
        if kind_err is not None:
            self._ctx.swallow_error(kind_err)
            return [], None

        total_amount_of_files_in_zip = len(job.zip_index.files)
        zip_index, filtered_zip_data = self._ctx.file_filter_factory.create(job.db, job.zip_index, job.config).select_filtered_files(job.zip_index)

        calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)
        file_packs, folder_packs = self._create_packages_from_index(calculator, zip_index)
        target_pkg, target_error = self._create_target_package(calculator, zip_kind, job.zip_description)
        if target_error is not None:
            self._ctx.swallow_error(target_error)
            return [], target_error

        logger.debug(f"Reserving space '{job.db.db_id} zip:{job.zip_id}...")
        logger.bench('Reserving space...')
        job.full_partitions = self._try_reserve_space(file_packs)
        if len(job.full_partitions) > 0:
            job.failed_files_no_space = file_packs
            logger.debug(f"Not enough space '{job.db.db_id} zip:{job.zip_id}'!")
            return [], FileWriteError(f"Could not allocate space for decompressing {len(file_packs)} files.")

        logger.bench('Precaching is_file...')
        self._ctx.file_system.precache_is_file_with_folders(folder_packs)

        files_to_unzip, already_processed_files = self._process_compressed_file_packages(file_packs, job.db.db_id, store, job.full_resync)
        if len(already_processed_files) > 0:
            already_processed = already_processed_files[0]
            logger.print(f'Skipping zip "{job.zip_id}" because file "{already_processed.pkg.rel_path}" was already processed by db "{already_processed.db_id}"')
            return [], None

        logger.bench('Creating folders...')
        job.removed_folders, job.installed_folders, job.failed_folders = process_create_folder_packages(self._ctx, folder_packs, job.db.db_id, zip_index.folders, store)
        if len(job.failed_folders) > 0:
            return [], FolderCreationError(f"Could not create {len(job.failed_folders)} folders.")

        job.filtered_data = filtered_zip_data[job.zip_id] if job.zip_id in filtered_zip_data else {'files': {}, 'folders': {}}

        if len(files_to_unzip) == 0:
            return [], None

        get_file_job, validate_job = make_get_zip_file_jobs(db=job.db, zip_id=job.zip_id, description=job.zip_description['contents_file'], tag=None)
        open_zip_contents_job = OpenZipContentsJob(
            db=job.db,
            store=job.store,
            ini_description=job.ini_description,
            config=job.config,
            full_resync=job.full_resync,

            zip_id=job.zip_id,
            zip_kind=zip_kind,
            target_folder=target_pkg,
            total_amount_of_files_in_zip=total_amount_of_files_in_zip,
            files_to_unzip=files_to_unzip,
            recipient_folders=job.installed_folders,
            contents_zip_temp_path=validate_job.target_file_path,
            action_text=job.zip_description['description'],
            zip_base_files_url=job.zip_description.get('base_files_url', '').strip(),
            filtered_data=job.filtered_data,

            get_file_job=get_file_job,
            make_process_index_backup=lambda: _make_process_index_job(job)
        )
        validate_job.after_job = open_zip_contents_job
        return [get_file_job], None

    def _create_packages_from_index(self, calculator: TargetPathsCalculator, zip_index: Index) -> Tuple[List[PathPackage], List[PathPackage]]:
        file_packs: List[PathPackage] = []
        for file_path, file_description in zip_index.files.items():
            file_pkg, file_error = calculator.deduce_target_path(file_path, file_description, PathType.FILE)
            if file_error is not None:
                self._ctx.swallow_error(file_error)

            file_packs.append(file_pkg)

        folder_packs: List[PathPackage] = []
        for folder_path, folder_description in zip_index.folders.items():
            folder_pkg, folder_error = calculator.deduce_target_path(folder_path, folder_description, PathType.FOLDER)
            if folder_error is not None:
                self._ctx.swallow_error(folder_error)

            folder_packs.append(folder_pkg)

        return file_packs, folder_packs

    def _create_target_package(self, calculator: TargetPathsCalculator, kind: ZipKind, description: Dict[str, Any]) -> Tuple[Optional[str], Optional[Exception]]:
        if kind == ZipKind.EXTRACT_ALL_CONTENTS:
            if 'target_folder_path' not in description or not isinstance(description['target_folder_path'], str):
                return None, Exception('extract_all_contents zip requires string "target_folder_path".')
            else:
                return calculator.deduce_target_path(description['target_folder_path'], {}, PathType.FOLDER)
        elif kind == ZipKind.EXTRACT_SINGLE_FILES:
            return None, None
        else: raise ValueError(f"Impossible kind '{kind}'")

    def _try_reserve_space(self, file_packs: List[PathPackage]) -> List[Tuple[Partition, int]]:
        fits_well, full_partitions = self._ctx.free_space_reservation.reserve_space_for_file_pkgs(file_packs)
        if fits_well:
            return []
        else:
            for partition, _ in full_partitions:
                self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")

            return full_partitions

    def _process_compressed_file_packages(self, file_packs: List[PathPackage], db_id: str, store: ReadOnlyStoreAdapter, full_resync: bool) -> Tuple[List[PathPackage], List[PathPackage]]:
        if full_resync:
            contained_files = file_packs
        else:
            existing_files, missing_files = self._ctx.file_system.are_files(file_packs)

            contained_files = [pkg for pkg in existing_files if store.hash_file(pkg.rel_path) != pkg.description.get('hash', None)]
            contained_files.extend(missing_files)

        return self._ctx.installation_report.add_processed_files(contained_files, db_id)

    def _fill_fragment_with_zip_index(self, fragment: StoreFragmentDrivePaths, job: ProcessZipJob):
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

        if path_pkg.pext_props and path_pkg.is_pext_external:
            drive = path_pkg.pext_props.drive
            fragment['external_paths'][drive] = {'files': {}, 'folders': {}}
            for file_path, file_description in job.zip_index.files.items():
                fragment['external_paths'][drive]['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['external_paths'][drive]['folders'][folder_path[1:]] = folder_description
        elif path_pkg.is_pext_standard:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path[1:]] = folder_description

        else:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path] = folder_description

def _make_process_index_job(job: ProcessZipJob) -> Optional[ProcessIndexJob]:
    if 'base_files_url' not in job.zip_description:
        for file_description in job.zip_index.files.values():
            if 'url' not in file_description:
                return None

    return ProcessIndexJob(
        db=job.db,
        ini_description=job.ini_description,
        config=job.config,
        index=job.zip_index,
        store=job.store.select(files=list(job.zip_index.files), folders=list(job.zip_index.folders)),
        full_resync=job.full_resync,
    )
