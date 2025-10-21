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

from itertools import chain
from typing import Dict, Any, List, Tuple, Optional, Set, Union, Iterable
import threading
import os
from collections import defaultdict

from downloader.config import FileChecking
from downloader.db_entity import check_file_pkg, check_folder_paths
from downloader.file_filter import BadFileFilterPartException, Config, ZipData
from downloader.file_system import FileWriteError, FolderCreationError, FsError, ReadOnlyFileSystem
from downloader.free_space_reservation import Partition
from downloader.job_system import Job, WorkerResult
from downloader.jobs.errors import WrongDatabaseOptions
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.path_package import PathPackage, PathType, PEXT_KIND_EXTERNAL, \
    PEXT_KIND_STANDARD, PATH_PACKAGE_KIND_PEXT
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.index import Index
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.local_store_wrapper import ReadOnlyStoreAdapter
from downloader.other import calculate_url
from downloader.target_path_calculator import TargetPathsCalculator, StoragePriorityError

_CheckFilePackage = PathPackage
_FetchFilePackage = PathPackage
_ValidateFilePackage = PathPackage
_AlreadyInstalledFilePackage = PathPackage
_RemoveFilePackage = PathPackage
_CreateFolderPackage = PathPackage
_DeleteFolderPackage = PathPackage


class ProcessDbIndexWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext) -> None:
        super().__init__(ctx)
        self._folders_created: Set[str] = set()
        self._lock = threading.Lock()

    def job_type_id(self) -> int: return ProcessDbIndexJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbIndexJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        zip_id, db, config, summary = job.zip_id, job.db, job.config, job.index
        store = job.store.read_only()

        logger.bench('ProcessDbIndexWorker start: ', db.db_id, zip_id)
        try:
            non_existing_pkgs, need_update_pkgs, created_folders, _, error = process_index_job_main_sequence(self._ctx, job, summary, store)
            if error is not None:
                return [], error

            logger.bench('ProcessDbIndexWorker fetch jobs: ', db.db_id, zip_id)
            next_jobs = create_fetch_jobs(self._ctx, db.db_id, non_existing_pkgs, need_update_pkgs, created_folders, db.base_files_url)
            logger.bench('ProcessDbIndexWorker done: ', db.db_id, zip_id)
            return next_jobs, None
        except (BadFileFilterPartException, StoragePriorityError, FsError, OSError) as e:
            self._ctx.swallow_error(WrongDatabaseOptions("Wrong custom download filter on database %s. Part '%s' is invalid." % (db.db_id, str(e))) if isinstance(e, BadFileFilterPartException) else e)
            return [], e

# @TODO(python 3.12): Use ProcessDbIndexJob & ProcessZipIndexJob instead of Union, which is incorrect
def process_index_job_main_sequence(ctx: DownloaderWorkerContext, job: Union[ProcessDbIndexJob, ProcessZipIndexJob], summary: Index, store: ReadOnlyStoreAdapter, /) -> Tuple[
    list[PathPackage],
    list[PathPackage],
    set[str],
    ZipData,
    Optional[Exception]
]:
    logger = ctx.logger
    config, db, zip_id, always_check_hash = job.config, job.db, job.zip_id, job.config['file_checking'] == FileChecking.ALWAYS_HASH

    bench_label = job.__class__.__name__
    logger.bench(bench_label, ' filter summary: ', db.db_id, zip_id)
    filtered_summary, zip_data = ctx.file_filter_factory.create(db, summary, config).select_filtered_files(summary)

    logger.bench(bench_label, ' create pkgs: ', db.db_id, zip_id)
    check_file_pkgs, job.files_to_remove, create_folder_pkgs, job.directories_to_remove = create_packages_from_index(ctx, config, filtered_summary, store)

    logger.bench(bench_label, ' checking duplicates: ', db.db_id, zip_id)
    job.non_duplicated_files, job.duplicated_files = ctx.installation_report.add_processed_files(check_file_pkgs)

    logger.bench(bench_label, ' Precaching is_file: ', db.db_id, zip_id)
    ctx.file_system.precache_is_file_with_folders(create_folder_pkgs)

    logger.bench(bench_label, ' check pkgs: ', db.db_id, zip_id)
    non_existing_pkgs, validate_pkgs, job.present_not_validated_files = process_check_file_packages(ctx, job.non_duplicated_files, db.db_id, store, always_check_hash, bench_label)

    logger.bench(bench_label, ' validate pkgs: ', db.db_id, zip_id)
    job.present_validated_files, job.skipped_updated_files, need_update_pkgs = process_validate_packages(ctx, validate_pkgs)

    if non_existing_pkgs or need_update_pkgs:
        logger.bench(bench_label, ' Reserve space: ', db.db_id, zip_id)
        need_install_pkgs = chain(non_existing_pkgs, need_update_pkgs)
        job.full_partitions = try_reserve_space(ctx, need_install_pkgs)
        if len(job.full_partitions) > 0:
            job.failed_files_no_space = non_existing_pkgs + need_update_pkgs
            logger.debug("Not enough space '%s'!", db.db_id)
            return [], [], set(), {}, FileWriteError(f"Could not allocate space for {len(job.failed_files_no_space)} files.")
    else:
        need_install_pkgs = None

    if need_install_pkgs is not None or job.present_validated_files:
        logger.bench(bench_label, ' Checking non external store presence: ', db.db_id, zip_id)
        job.repeated_store_presence = check_repeated_store_presence(ctx, store, chain(need_install_pkgs or [], job.present_validated_files))

    logger.bench(bench_label, ' Create folders: ', db.db_id, zip_id)
    job.removed_folders, job.installed_folders, created_folders, job.failed_folders = process_create_folder_packages(ctx, create_folder_pkgs, db.db_id, filtered_summary.folders, store)
    if len(job.failed_folders) > 0:
        return [], [], set(), {}, FolderCreationError(f"Could not create {len(job.failed_folders)} folders.")

    return non_existing_pkgs, need_update_pkgs, created_folders, zip_data, None

def create_packages_from_index(ctx: DownloaderWorkerContext, config: Config, summary: Index, store: ReadOnlyStoreAdapter) -> Tuple[
    List[_CheckFilePackage],
    List[_RemoveFilePackage],
    List[_CreateFolderPackage],
    List[_DeleteFolderPackage]
]:
    calculator = ctx.target_paths_calculator_factory.target_paths_calculator(config)
    check_file_pkgs, remove_files_pkgs = _translate_items(ctx, calculator, summary.files, PathType.FILE, store.all_files())
    create_folder_pkgs, delete_folder_pkgs = _translate_items(ctx, calculator, summary.folders, PathType.FOLDER, store.all_folders())
    return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs

def _translate_items(ctx: DownloaderWorkerContext, calculator: TargetPathsCalculator, items: Dict[str, Dict[str, Any]], path_type: PathType, stored: Dict[str, Dict[str, Any]]) -> Tuple[List[PathPackage], List[PathPackage]]:
    present, present_errors = calculator.create_path_packages(items.items(), path_type)
    present_set = {pkg.rel_path for pkg in present}
    removed, removed_errors = calculator.create_path_packages([(path, description) for path, description in stored.items() if path not in present_set], path_type)

    for e in removed_errors:
        ctx.swallow_error(e)
    for e in present_errors:
        ctx.swallow_error(e)

    return present, removed

def process_check_file_packages(ctx: DownloaderWorkerContext, non_duplicated_pkgs: List[_CheckFilePackage], db_id: str, store: ReadOnlyStoreAdapter, always_check_hash: bool, bench_label: str) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage], List[_AlreadyInstalledFilePackage]]:
    if len(non_duplicated_pkgs) == 0:
        return [], [], []

    file_system = ReadOnlyFileSystem(ctx.file_system)

    ctx.logger.bench(bench_label, ' file_system check: ', db_id, len(non_duplicated_pkgs))
    existing, non_existing_pkgs = file_system.are_files(non_duplicated_pkgs)

    ctx.logger.bench(bench_label, ' existing loop: ', db_id, len(non_duplicated_pkgs))
    already_installed_pkgs: List[_ValidateFilePackage]
    validate_pkgs: List[_ValidateFilePackage]
    if always_check_hash:
        validate_pkgs = existing  # @TODO: Cover this scenario in tests
        already_installed_pkgs = []
    else:
        ctx.logger.bench('invalid hashes start: ', db_id, len(non_duplicated_pkgs))
        invalid_hashes = store.invalid_hashes(existing)
        ctx.logger.bench('invalid hashes end: ', db_id, len(non_duplicated_pkgs))
        if any(invalid_hashes):
            validate_pkgs = [pkg for pkg, inv in zip(existing, invalid_hashes) if inv]
            already_installed_pkgs = [pkg for pkg, inv in zip(existing, invalid_hashes) if not inv]
        else:
            validate_pkgs = []
            already_installed_pkgs = existing

    return non_existing_pkgs, validate_pkgs, already_installed_pkgs


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


def try_reserve_space(ctx: DownloaderWorkerContext, file_pkgs: Iterable[PathPackage]) -> List[Tuple[Partition, int]]:
    fits_well, full_partitions = ctx.free_space_reservation.reserve_space_for_file_pkgs(file_pkgs)
    if fits_well:
        return []
    else:
        for partition, _ in full_partitions:
            ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")

        return full_partitions

def check_repeated_store_presence(ctx: DownloaderWorkerContext, store: ReadOnlyStoreAdapter, keep_store_candidate_pkgs: Iterable[PathPackage]) -> set[str]:
    result = set()
    for pkg in keep_store_candidate_pkgs:
        if not pkg.is_pext_external():
            continue

        for _, drive in store.list_other_drives_for_file(pkg.rel_path, pkg.drive):
            if ctx.file_system.is_file(os.path.join(drive, pkg.rel_path), use_cache=False):
                result.add(pkg.rel_path)  # @TODO: See if use_cache is needed, and if we should optimize this fs access
    return result

def process_create_folder_packages(ctx: DownloaderWorkerContext, create_folder_pkgs: List[PathPackage], db_id: str, db_folder_index: Dict[str, Any], store: ReadOnlyStoreAdapter) -> Tuple[
    list[PathPackage],
    list[PathPackage],
    set[str],
    list[str]
]:
    if len(create_folder_pkgs) == 0:
        return [], [], set(), []

    try:
        check_folder_paths([pkg.rel_path for pkg in create_folder_pkgs], db_id)
    except Exception as e:
        ctx.swallow_error(e)

    folder_copies_to_be_removed: List[PathPackage] = []
    processing_folders: List[PathPackage] = []

    parent_drives: Dict[str, set[str]] = defaultdict(set)
    parent_pkgs: Dict[str, PathPackage] = dict()

    for pkg in sorted(create_folder_pkgs, key=lambda x: len(x.rel_path)):
        if pkg.is_pext_parent():
            parent_pkgs[pkg.rel_path] = pkg
            continue

        processing_folders.append(pkg)
        if pkg.kind != PATH_PACKAGE_KIND_PEXT or pkg.pext_props is None:
            continue

        pkg_parent = pkg.pext_props.parent
        if pkg_parent not in parent_pkgs or pkg.drive in parent_drives:
            continue

        parent_drives[pkg_parent].add(pkg.drive or pkg_parent)
        parent_pkg = parent_pkgs[pkg_parent].clone()
        parent_pkg.drive = pkg.drive
        parent_pkg.pext_props.kind = pkg.pext_props.kind  # type: ignore[union-attr]
        parent_pkg.pext_props.drive = pkg.pext_props.drive  # type: ignore[union-attr]
        parent_pkg.pext_props.parent = ''  # type: ignore[union-attr]
        processing_folders.append(parent_pkg)

    for pkg in processing_folders:
        folder_path, drive = pkg.rel_path, pkg.drive
        for is_external, other_drive in store.list_other_drives_for_folder(pkg):
            if ctx.file_system.is_folder(os.path.join(other_drive, folder_path)):
                continue

            if is_external:
                removed_pkg = pkg.clone_as_pext()
                removed_pkg.drive = other_drive
                removed_pkg.pext_props.drive = other_drive  # type: ignore[union-attr]
                removed_pkg.pext_props.kind = PEXT_KIND_EXTERNAL  # type: ignore[union-attr]
            else:
                removed_pkg = pkg.clone()
                removed_pkg.drive = other_drive
                if removed_pkg.pext_props is not None:
                    removed_pkg.pext_props.kind = PEXT_KIND_STANDARD
                    removed_pkg.pext_props.drive = other_drive

            folder_copies_to_be_removed.append(removed_pkg)

    ctx.logger.bench('add_processed_folders start: ', db_id, len(processing_folders))
    non_existing_folders = ctx.installation_report.add_processed_folders(processing_folders, db_id)
    ctx.logger.bench('add_processed_folders done: ', db_id, len(processing_folders))

    errors = []
    created_folders = set()

    for folder_pkg in sorted(non_existing_folders, key=lambda x: len(x.rel_path)):
        try:
            ctx.file_system.make_dirs(folder_pkg.full_path)
        except FolderCreationError as e:
            ctx.swallow_error(e)
            errors.append(folder_pkg.full_path)
        else:
            created_folders.add(folder_pkg.full_path)

    installed_folders = [f for f in processing_folders if f.db_path() in db_folder_index]
    return folder_copies_to_be_removed, installed_folders, created_folders, errors

def create_fetch_jobs(ctx: DownloaderWorkerContext, db_id: str, non_existing_pkgs: list[_FetchFilePackage], need_update_pkgs: list[_FetchFilePackage], created_folders: set[str], base_files_url: str) -> List[Job]:
    if len(non_existing_pkgs) == 0 and len(need_update_pkgs) == 0:
        return []

    return [
        job for job in chain(
            (_fetch_job(ctx, pkg, False, db_id, created_folders, base_files_url) for pkg in non_existing_pkgs),
            (_fetch_job(ctx, pkg,  True, db_id, created_folders, base_files_url) for pkg in need_update_pkgs)
        ) if job is not None
    ]

def _fetch_job(ctx: DownloaderWorkerContext, pkg: PathPackage, exists: bool, db_id: str, created_folders: set[str], base_files_url: str, /) -> Optional[FetchFileJob]:
    source = _url(file_path=pkg.rel_path, file_description=pkg.description, base_files_url=base_files_url)
    try:
        check_file_pkg(pkg, db_id, source)
    except Exception as e:
        ctx.swallow_error(e)
        return None

    parent_folder = pkg.parent
    if parent_folder and pkg.drive is not None:
        parent_full_path = pkg.drive + '/' + parent_folder
        if parent_full_path not in created_folders:
            ctx.file_system.make_dirs(parent_full_path)

    fetch_job = FetchFileJob(source, exists, pkg, db_id)
    return fetch_job
