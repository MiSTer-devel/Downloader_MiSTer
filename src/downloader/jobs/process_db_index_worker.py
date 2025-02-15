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

from typing import Dict, Any, List, Tuple, Optional, Set
from pathlib import Path
import threading
import os
from collections import defaultdict

from downloader.db_entity import DbEntity
from downloader.file_filter import BadFileFilterPartException, Config, ZipData
from downloader.file_system import FileWriteError, FolderCreationError, FsError, ReadOnlyFileSystem
from downloader.free_space_reservation import Partition
from downloader.job_system import Job, WorkerResult
from downloader.jobs.errors import WrongDatabaseOptions
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.path_package import PathExists, PathPackage, PathType, RemovedCopy
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.index import Index
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.local_store_wrapper import ReadOnlyStoreAdapter
from downloader.other import calculate_url
from downloader.target_path_calculator import TargetPathsCalculator, StoragePriorityError

_CheckFilePackage = PathPackage
_FetchFilePackage = PathPackage
_ValidateFilePackage = PathPackage
_MovedFilePackage = PathPackage
_AlreadyInstalledFilePackage = PathPackage
_RemoveFilePackage = PathPackage
_CreateFolderPackage = PathPackage
_DeleteFolderPackage = PathPackage


class ProcessDbIndexWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._folders_created: Set[str] = set()
        self._lock = threading.Lock()

    def job_type_id(self) -> int: return ProcessDbIndexJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbIndexJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        zip_id, db, config, summary, full_resync = job.zip_id, job.db, job.config, job.index, job.full_resync
        store = job.store.read_only()

        try:
            logger.bench('ProcessDbIndexWorker create pkgs: ', db.db_id, zip_id)
            check_file_pkgs, job.files_to_remove, create_folder_pkgs, job.directories_to_remove, _ = create_packages_from_index(self._ctx, config, summary, db, store, zip_id is not None)

            logger.bench('ProcessDbIndexWorker Precaching is_file: ', db.db_id, zip_id)
            self._ctx.file_system.precache_is_file_with_folders(create_folder_pkgs)

            logger.bench('ProcessDbIndexWorker check pkgs: ', db.db_id, zip_id)
            fetch_pkgs, validate_pkgs, job.present_not_validated_files = process_check_file_packages(self._ctx, check_file_pkgs, db.db_id, store, full_resync)

            logger.bench('ProcessDbIndexWorker validate pkgs: ', db.db_id, zip_id)
            job.present_validated_files, job.skipped_updated_files, more_fetch_pkgs = process_validate_packages(self._ctx, validate_pkgs)
            fetch_pkgs.extend(more_fetch_pkgs)

            logger.bench('ProcessDbIndexWorker Reserve space: ', db.db_id, zip_id)
            job.full_partitions = try_reserve_space(self._ctx, fetch_pkgs)
            if len(job.full_partitions) > 0:
                job.failed_files_no_space = fetch_pkgs
                logger.debug("Not enough space '%s'!", db.db_id)
                return [], FileWriteError(f"Could not allocate space for {len(fetch_pkgs)} files.")

            logger.bench('ProcessDbIndexWorker Create folders: ', db.db_id, zip_id)
            job.removed_folders, job.installed_folders, job.failed_folders = process_create_folder_packages(self._ctx, create_folder_pkgs, db.db_id, db.folders, store)
            if len(job.failed_folders) > 0:
                return [], FolderCreationError(f"Could not create {len(job.failed_folders)} folders.")

            logger.bench('ProcessDbIndexWorker fetch jobs: ', db.db_id, zip_id)
            next_jobs = create_fetch_jobs(self._ctx, db.db_id, fetch_pkgs, db.base_files_url)
            logger.bench('ProcessDbIndexWorker done: ', db.db_id, zip_id)
            return next_jobs, None
        except (BadFileFilterPartException, StoragePriorityError, FsError, OSError) as e:
            self._ctx.swallow_error(WrongDatabaseOptions("Wrong custom download filter on database %s. Part '%s' is invalid." % (db.db_id, str(e))) if isinstance(e, BadFileFilterPartException) else e)
            return [], e


def create_packages_from_index(ctx: DownloaderWorkerContext, config: Config, summary: Index, db: DbEntity, store: ReadOnlyStoreAdapter, from_zip: bool) -> Tuple[
    List[_CheckFilePackage],
    List[_RemoveFilePackage],
    List[_CreateFolderPackage],
    List[_DeleteFolderPackage],
    ZipData
]:
    filtered_summary, zip_data = ctx.file_filter_factory.create(db, summary, config).select_filtered_files(summary)

    summary_folders = _folders_with_missing_parents(ctx, filtered_summary, store, db, from_zip)
    calculator = ctx.target_paths_calculator_factory.target_paths_calculator(config)

    check_file_pkgs, files_set = _translate_items(ctx, calculator, filtered_summary.files, PathType.FILE, set())
    remove_files_pkgs, _ = _translate_items(ctx, calculator, store.files, PathType.FILE, files_set)
    create_folder_pkgs, folders_set = _translate_items(ctx, calculator, summary_folders, PathType.FOLDER, set())
    delete_folder_pkgs, _ = _translate_items(ctx, calculator, store.folders, PathType.FOLDER, folders_set)

    return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs, zip_data

def _folders_with_missing_parents(ctx: DownloaderWorkerContext, index: Index, store: ReadOnlyStoreAdapter, db: DbEntity, from_zip: bool) -> Dict[str, Any]:
    if len(index.files) == 0 and len(index.folders) == 0:
        return index.folders

    result_folders: Dict[str, Any] = {}
    for collection, col_ctx in ((index.files, 'file'), (index.folders, 'folder')):
        for path in collection:
            path_obj = Path(path)
            for parent_obj in list(path_obj.parents)[:-1]:  # @TODO: Optimize .parents iteration
                parent_str = str(parent_obj)
                if parent_str in index.folders or parent_str in result_folders: continue

                result_folders[parent_str] = store.folders.get(parent_str, {})
                if from_zip:
                    pass  # @TODO: This whole from_zip should not be needed. But we need to avoid a warning because it always fails now. This is happening because pext_parent folder loses the zip_id in the store.
                else:
                   ctx.logger.print(f"Warning: Database [{db.db_id}] should contain {col_ctx} '{parent_str}' because of {col_ctx} '{path}'. The database maintainer should fix this.")

    if len(result_folders) > 0:
        result_folders.update(index.folders)
        return result_folders
    else:
        return index.folders

def _translate_items(ctx: DownloaderWorkerContext, calculator: TargetPathsCalculator, items: Dict[str, Dict[str, Any]], path_type: PathType, exclude: Set[str]) -> Tuple[List[PathPackage], Set[str]]:
    translated = []
    rel_set = set()
    for path, description in items.items():
        pkg, error = calculator.deduce_target_path(path, description, path_type)
        if error is not None:
           ctx.swallow_error(error)

        if pkg.rel_path in exclude: continue

        translated.append(pkg)
        rel_set.add(pkg.rel_path)

    return translated, rel_set


def process_check_file_packages(ctx: DownloaderWorkerContext, check_file_pkgs: List[_CheckFilePackage], db_id: str, store: ReadOnlyStoreAdapter, full_resync: bool) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage], List[_MovedFilePackage], List[_AlreadyInstalledFilePackage]]:
    if len(check_file_pkgs) == 0:
        return [], [], []

    file_system = ReadOnlyFileSystem(ctx.file_system)

    non_duplicated_pkgs, duplicated_files = ctx.installation_report.add_processed_files(check_file_pkgs, db_id)
    for dup in duplicated_files:
        ctx.file_download_session_logger.print_progress_line(f'DUPLICATED: {dup.pkg.rel_path} [using {dup.db_id} instead]')

    fetch_pkgs: List[_FetchFilePackage] = []
    validate_pkgs: List[_ValidateFilePackage] = []
    already_installed_pkgs: List[_ValidateFilePackage] = []

    existing, missing = file_system.are_files(non_duplicated_pkgs)

    for pkg in missing: pkg.exists = PathExists.DOES_NOT_EXIST
    fetch_pkgs.extend(missing)

    for pkg in existing:
        pkg.exists = PathExists.EXISTS

        if full_resync or (store.hash_file(pkg.rel_path) != pkg.description['hash']):
            validate_pkgs.append(pkg)
            continue

        if store.is_file_in_drive(pkg.rel_path, pkg.pext_drive()):
            already_installed_pkgs.append(pkg)
        else:
            validate_pkgs.append(pkg)

    return fetch_pkgs, validate_pkgs, already_installed_pkgs


def process_validate_packages(ctx: DownloaderWorkerContext, validate_pkgs: List[_ValidateFilePackage]) -> Tuple[List[PathPackage], List[PathPackage], List[_FetchFilePackage]]:
    if len(validate_pkgs) == 0:
        return [], [], []

    file_system = ReadOnlyFileSystem(ctx.file_system)

    more_fetch_pkgs: List[_FetchFilePackage] = []
    present_validated_files: List[_FetchFilePackage] = []
    skipped_updated_files: List[_FetchFilePackage] = []

    for pkg in validate_pkgs:
        # @TODO: Parallelize the slow hash calculations
        if file_system.hash(pkg.full_path) == pkg.description['hash']:
            ctx.file_download_session_logger.print_progress_line(f'No changes: {pkg.rel_path}')
            present_validated_files.append(pkg)
            continue

        if 'overwrite' in pkg.description and not pkg.description['overwrite']:
            if file_system.hash(pkg.full_path) != pkg.description['hash']:
                skipped_updated_files.append(pkg)
            else:
                present_validated_files.append(pkg)

            continue

        more_fetch_pkgs.append(pkg)

    return present_validated_files, skipped_updated_files, more_fetch_pkgs

def _url(file_path: str, file_description: Dict[str, Any], base_files_url: str) -> Any:
    return file_description['url'] if 'url' in file_description else calculate_url(base_files_url, file_path if file_path[0] != '|' else file_path[1:])


def try_reserve_space(ctx: DownloaderWorkerContext, file_pkgs: List[PathPackage]) -> List[Tuple[Partition, int]]:
    if len(file_pkgs) == 0:
        return []

    fits_well, full_partitions = ctx.free_space_reservation.reserve_space_for_file_pkgs(file_pkgs)
    if fits_well:
        return []
    else:
        for partition, _ in full_partitions:
            ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")

        return full_partitions


def process_create_folder_packages(ctx: DownloaderWorkerContext, create_folder_pkgs: List[PathPackage], db_id: str, db_folder_index: Dict[str, Any], store: ReadOnlyStoreAdapter) -> Tuple[List[RemovedCopy], List[PathPackage], List[str]]:
    if len(create_folder_pkgs) == 0:
        return [], [], []

    folder_copies_to_be_removed: List[Tuple[bool, str, str, PathType]] = []
    parents: Dict[str, Dict[str, PathPackage]] = defaultdict(defaultdict)
    processing_folders: List[PathPackage] = []
    parent_pkgs: Dict[str, PathPackage] = dict()

    for pkg in sorted(create_folder_pkgs, key=lambda x: len(x.rel_path)):
        if pkg.is_pext_parent:
            parent_pkgs[pkg.rel_path] = pkg
            continue

        processing_folders.append(pkg)

        if pkg.pext_props:
            if pkg.pext_props.drive not in parents[pkg.pext_props.parent]:
                parents[pkg.pext_props.parent][pkg.pext_props.drive] = pkg.pext_props.parent_pkg()
                if pkg.pext_props.parent in parent_pkgs:
                    parents[pkg.pext_props.parent][pkg.pext_props.drive].description = parent_pkgs[pkg.pext_props.parent].description

        _maybe_add_copies_to_remove(ctx, folder_copies_to_be_removed, store, pkg.rel_path, pkg.pext_drive())

    for parent_path, drives in parents.items():
        for d, parent_pkg in drives.items():
            processing_folders.append(parent_pkg)
            _maybe_add_copies_to_remove(ctx, folder_copies_to_be_removed, store, parent_path, d)

    non_existing_folders = ctx.installation_report.add_processed_folders(processing_folders, db_id)
    to_create = {folder_pkg.full_path for folder_pkg in non_existing_folders}

    errors = []
    for full_folder_path in sorted(to_create, key=lambda x: len(x)):
        try:
            ctx.file_system.make_dirs(full_folder_path)
        except FolderCreationError as e:
            ctx.swallow_error(e)
            errors.append(full_folder_path)

    installed_folders = [f for f in processing_folders if f.db_path() in db_folder_index]
    return folder_copies_to_be_removed, installed_folders, errors

def _maybe_add_copies_to_remove(ctx: DownloaderWorkerContext, copies: List[Tuple[bool, str, str, PathType]], store: ReadOnlyStoreAdapter, folder_path: str, drive: Optional[str]):
    if store.folder_drive(folder_path) == drive: return
    copies.extend([
        (is_external, folder_path, other_drive, PathType.FOLDER)
        for is_external, other_drive in store.list_other_drives_for_folder(folder_path, drive)
        if not ctx.file_system.is_folder(os.path.join(other_drive, folder_path))
    ])


def create_fetch_jobs(ctx: DownloaderWorkerContext, db_id: str, fetch_pkgs: List[_FetchFilePackage], base_files_url: str) -> List[Job]:
    if len(fetch_pkgs) == 0:
        return []

    jobs: List[Job] = []
    for pkg in fetch_pkgs:
        source = _url(file_path=pkg.rel_path, file_description=pkg.description, base_files_url=base_files_url)
        if not isinstance(source, str):
            ctx.swallow_error(Exception(f"Invalid 'url' for file '{pkg.rel_path}' at database '{db_id}'."))
            continue

        temp_path = pkg.temp_path()
        fetch_job = FetchFileJob(
            source=source,
            info=pkg.rel_path,
            temp_path=temp_path,
            silent=False
        )
        fetch_job.after_job = ValidateFileJob(
            temp_path=temp_path,
            target_file_path=pkg.full_path,
            description=pkg.description,
            info=pkg.rel_path,
            backup_path=pkg.backup_path(),
            get_file_job=fetch_job
        )
        fetch_job.add_tag(db_id)
        fetch_job.after_job.add_tag(db_id)
        jobs.append(fetch_job)

    return jobs
