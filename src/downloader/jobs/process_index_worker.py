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
from downloader.file_filter import FileFilterFactory, BadFileFilterPartException, Config
from downloader.file_system import FsError, ReadOnlyFileSystem
from downloader.free_space_reservation import Partition
from downloader.job_system import Job, WorkerResult
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.path_package import PathPackage, PathType, RemovedCopy
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.index import Index
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.constants import FILE_MiSTer, FILE_MiSTer_old
from downloader.local_store_wrapper import ReadOnlyStoreAdapter
from downloader.other import calculate_url
from downloader.storage_priority_resolver import StoragePriorityError
from downloader.target_path_calculator import TargetPathsCalculator

_CheckFilePackage = PathPackage
_FetchFilePackage = PathPackage
_ValidateFilePackage = PathPackage
_MovedFilePackage = PathPackage
_AlreadyInstalledFilePackage = PathPackage
_RemoveFilePackage = PathPackage
_CreateFolderPackage = PathPackage
_DeleteFolderPackage = PathPackage


class ProcessIndexWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._folders_created: Set[str] = set()
        self._lock = threading.Lock()

    def job_type_id(self) -> int: return ProcessIndexJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessIndexJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        db, config, summary, full_resync = job.db, job.config, job.index, job.full_resync
        store = job.store.read_only()

        try:
            logger.debug(f"Processing db '{db.db_id}'...")
            check_file_pkgs, job.files_to_remove, create_folder_pkgs, job.directories_to_remove = self._create_packages_from_index(config, summary, db, store)

            logger.debug(f"Processing check file packages '{db.db_id}'...")
            fetch_pkgs, validate_pkgs, moved_pkgs, job.present_not_validated_files = self._process_check_file_packages(check_file_pkgs, db.db_id, store, full_resync)

            logger.debug(f"Processing validate file packages '{db.db_id}'...")
            job.present_validated_files, job.skipped_updated_files, more_fetch_pkgs = self._process_validate_packages(validate_pkgs)
            fetch_pkgs.extend(more_fetch_pkgs)

            logger.debug(f"Processing moved file packages '{db.db_id}'...")
            job.removed_copies = self._process_moved_packages(moved_pkgs, store)

            self._ctx.file_download_session_logger.print_header(db, nothing_to_download=len(fetch_pkgs) == 0)

            logger.debug(f"Reserving space '{db.db_id}'...")
            job.full_partitions = self._try_reserve_space(fetch_pkgs)
            if len(job.full_partitions) > 0:
                job.failed_files_no_space = fetch_pkgs
                logger.debug(f"Not enough space '{db.db_id}'!")
                return [], None # @TODO return error instead to retry later?

            logger.debug(f"Processing create folder packages '{db.db_id}'...")
            removed_folders, job.installed_folders = self._process_create_folder_packages(create_folder_pkgs, db, store)  # @TODO maybe move this one after reserve space
            job.removed_copies.extend(removed_folders)

            logger.debug(f"Process fetch packages and launch fetch jobs '{db.db_id}'...")
            next_jobs = self._process_fetch_packages_and_launch_jobs(fetch_pkgs, db.base_files_url)
            return next_jobs, None
        except (BadFileFilterPartException, StoragePriorityError, FsError, OSError) as e:
            return [], e

    def _create_packages_from_index(self, config: Config, summary: Index, db: DbEntity, store: ReadOnlyStoreAdapter) -> Tuple[
        List[_CheckFilePackage],
        List[_RemoveFilePackage],
        List[_CreateFolderPackage],
        List[_DeleteFolderPackage]
    ]:
        logger = self._ctx.logger

        logger.bench('Filtering Database...')
        filtered_summary, _ = FileFilterFactory(self._ctx.logger)\
            .create(db, summary, config)\
            .select_filtered_files(summary)

        logger.bench('Translating paths...')
        summary_folders = self._folders_with_missing_parents(filtered_summary, store, db)
        calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(config)

        check_file_pkgs, files_set = self._translate_items(calculator, filtered_summary.files, PathType.FILE, set())
        remove_files_pkgs, _ = self._translate_items(calculator, store.files, PathType.FILE, files_set)
        create_folder_pkgs, folders_set = self._translate_items(calculator, summary_folders, PathType.FOLDER, set())
        delete_folder_pkgs, _ = self._translate_items(calculator, store.folders, PathType.FOLDER, folders_set)

        # @TODO REFACTOR: This looks wrong
        # remove_files_pkgs = [pkg for pkg in remove_files_pkgs if 'zip_id' not in pkg.description]

        # @TODO REFACTOR: This looks wrong
        # delete_folder_pkgs = [pkg for pkg in delete_folder_pkgs if 'zip_id' not in pkg.description]

        # @TODO commenting these 2 lines make the test still pass, why?
        for pkg in check_file_pkgs:
            if pkg.rel_path is FILE_MiSTer: pkg.description['backup'] = FILE_MiSTer_old

        return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs

    def _folders_with_missing_parents(self, index: Index, store: ReadOnlyStoreAdapter, db: DbEntity) -> Dict[str, Any]:
        if len(index.files) == 0 and len(index.folders) == 0:
            return index.folders

        result_folders: Dict[str, Any] = {}
        for collection, col_ctx in ((index.files, 'file'), (index.folders, 'folder')):
            for path in collection:
                path_obj = Path(path)
                for parent_obj in path_obj.parents[:-1]:
                    parent_str = str(parent_obj)
                    if parent_str in index.folders or parent_str in result_folders: continue

                    result_folders[parent_str] = store.folders.get(parent_str, {})
                    self._ctx.logger.print(f"Warning: Database [{db.db_id}] should contain {col_ctx} '{parent_str}' because of {col_ctx} '{path}'. The database maintainer should fix this.")

        if len(result_folders) > 0:
            result_folders.update(index.folders)
            return result_folders
        else:
            return index.folders

    @staticmethod
    def _translate_items(calculator: TargetPathsCalculator, items: Dict[str, Dict[str, Any]], path_type: PathType, exclude: Set[str]) -> Tuple[List[PathPackage], Set[str]]:
        translated = []
        rel_set = set()
        for path, description in items.items():
            pkg = calculator.deduce_target_path(path, description, path_type)
            if pkg.rel_path in exclude: continue

            translated.append(pkg)
            rel_set.add(pkg.rel_path)

        return translated, rel_set

    def _process_check_file_packages(self, check_file_pkgs: List[_CheckFilePackage], db_id: str, store: ReadOnlyStoreAdapter, full_resync: bool) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage], List[_MovedFilePackage], List[_AlreadyInstalledFilePackage]]:
        if len(check_file_pkgs) == 0:
            return [], [], [], []

        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        non_duplicated_pkgs, duplicated_files = self._ctx.installation_report.add_processed_files(check_file_pkgs, db_id)
        for dup in duplicated_files:
            self._ctx.file_download_session_logger.print_progress_line(f'DUPLICATED: {dup.pkg.rel_path} [using {dup.db_id} instead]')

        fetch_pkgs: List[_FetchFilePackage] = []
        validate_pkgs: List[_ValidateFilePackage] = []
        moved_pkgs: List[_ValidateFilePackage] = []
        already_installed_pkgs: List[_ValidateFilePackage] = []
        for pkg in non_duplicated_pkgs:
            if not file_system.is_file(pkg.full_path):
                fetch_pkgs.append(pkg)
                continue

            if full_resync or (store.hash_file(pkg.rel_path) != pkg.description['hash']):
                validate_pkgs.append(pkg)
                continue

            if store.is_file_in_drive(pkg.rel_path, pkg.drive()):
                already_installed_pkgs.append(pkg)
            else:
                validate_pkgs.append(pkg)
                moved_pkgs.append(pkg)

        return fetch_pkgs, validate_pkgs, moved_pkgs, already_installed_pkgs

    def _process_validate_packages(self, validate_pkgs: List[_ValidateFilePackage]) -> Tuple[List[PathPackage], List[PathPackage], List[_FetchFilePackage]]:
        if len(validate_pkgs) == 0:
            return [], [], []

        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        more_fetch_pkgs: List[_FetchFilePackage] = []
        present_validated_files: List[_FetchFilePackage] = []
        skipped_updated_files: List[_FetchFilePackage] = []

        for pkg in validate_pkgs:
            # @TODO: Parallelize the slow hash calculations
            if file_system.hash(pkg.full_path) == pkg.description['hash']:
                self._ctx.file_download_session_logger.print_progress_line(f'No changes: {pkg.rel_path}')
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

    def _process_moved_packages(self, moved_pkgs: List[_MovedFilePackage], store: ReadOnlyStoreAdapter) -> List[RemovedCopy]:
        if len(moved_pkgs) == 0:
            return []

        moved_files: List[Tuple[bool, str, str, PathType]] = []
        for pkg in moved_pkgs:
            for is_external, other_drive in store.list_other_drives_for_file(pkg.rel_path, pkg.drive()):
                other_file = os.path.join(other_drive, pkg.rel_path)
                if not self._ctx.file_system.is_file(other_file):
                    moved_files.append((is_external, pkg.rel_path, other_drive, PathType.FILE))

        return moved_files

    def _try_reserve_space(self, fetch_pkgs: List[_FetchFilePackage]) -> List[Tuple[Partition, int]]:
        if len(fetch_pkgs) == 0:
            return []

        fits_well, full_partitions = self._ctx.free_space_reservation.reserve_space_for_file_pkgs(fetch_pkgs)
        if fits_well:
            return []
        else:
            for partition, _ in full_partitions:
                self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")

            return full_partitions

    def _process_create_folder_packages(self, create_folder_pkgs: List[_CreateFolderPackage], db: DbEntity, store: ReadOnlyStoreAdapter) -> Tuple[List[RemovedCopy], List[PathPackage]]:
        if len(create_folder_pkgs) == 0:
            return [], []

        folders_to_create: Set[str] = set()
        folder_copies_to_be_removed: List[Tuple[bool, str, str, PathType]] = []
        parents: Dict[str, Set[str]] = defaultdict(set)

        for pkg in create_folder_pkgs:
            if pkg.is_pext_parent:
                continue

            if pkg.pext_props is not None:
                parents[pkg.pext_props.parent].add(pkg.pext_props.drive)
                folders_to_create.add(pkg.pext_props.parent_full_path())

            folders_to_create.add(pkg.full_path)
            self._maybe_add_copies_to_remove(folder_copies_to_be_removed, store, pkg.rel_path, pkg.drive())

        for parent_path, drives in parents.items():
            for d in drives:
                self._maybe_add_copies_to_remove(folder_copies_to_be_removed, store, parent_path, d)

        with self._lock:
            folders_to_create = folders_to_create - self._folders_created
            if len(folders_to_create) > 0:
                self._folders_created.update(folders_to_create)

        for full_folder_path in sorted(folders_to_create, key=lambda x: len(x), reverse=True):
            self._ctx.file_system.make_dirs(full_folder_path)

        # @TODO Why two adds?
        folders = [f for f in create_folder_pkgs if f.db_path() in db.folders]
        self._ctx.installation_report.add_processed_folders(folders, db.db_id)

        return folder_copies_to_be_removed, folders

    def _maybe_add_copies_to_remove(self, copies: List[Tuple[bool, str, str, PathType]], store: ReadOnlyStoreAdapter, folder_path: str, drive: Optional[str]):
        if store.folder_drive(folder_path) == drive: return
        copies.extend([
            (is_external, folder_path, other_drive, PathType.FOLDER)
            for is_external, other_drive in store.list_other_drives_for_folder(folder_path, drive)
            if not self._ctx.file_system.is_folder(os.path.join(other_drive, folder_path))
        ])

    @staticmethod
    def _process_fetch_packages_and_launch_jobs(fetch_pkgs: List[_FetchFilePackage], base_files_url: str) -> List[Job]:
        if len(fetch_pkgs) == 0:
            return []

        jobs: List[Job] = []
        for pkg in fetch_pkgs:
            download_path = pkg.full_path + '.new'
            fetch_job = FetchFileJob2(
                source=_url(file_path=pkg.rel_path, file_description=pkg.description, base_files_url=base_files_url),
                info=pkg.rel_path,
                temp_path=download_path,
                silent=False
            )
            fetch_job.after_job = ValidateFileJob2(
                temp_path=download_path,
                target_file_path=pkg.full_path,
                description=pkg.description,
                info=pkg.rel_path,
                get_file_job=fetch_job
            )
            jobs.append(fetch_job)

        return jobs


def _url(file_path: str, file_description: Dict[str, Any], base_files_url: str):
    return file_description['url'] if 'url' in file_description else calculate_url(base_files_url, file_path if file_path[0] != '|' else file_path[1:])
