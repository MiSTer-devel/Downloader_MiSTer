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
from downloader.file_filter import FileFilterFactory, BadFileFilterPartException
from downloader.file_system import ReadOnlyFileSystem
from downloader.job_system import Job, WorkerResult
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.path_package import PathPackage, PathPackageKind, PathType
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.index import Index
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.constants import FILE_MiSTer, FILE_MiSTer_old, K_BASE_PATH
from downloader.local_store_wrapper import NO_HASH_IN_STORE_CODE, ReadOnlyStoreAdapter
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

    def operate_on(self, job: ProcessIndexJob) -> WorkerResult:
        logger = self._ctx.logger
        db, config, summary, full_resync = job.db, job.config, job.index, job.full_resync
        store = job.store.read_only()

        try:
            logger.debug(f"Processing db '{db.db_id}'...")
            check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs = self._create_packages_from_index(config, summary, db, store)

            logger.debug(f"Processing check file packages '{db.db_id}'...")
            fetch_pkgs, validate_pkgs, moved_pkgs, already_installed_pkgs = self._process_check_file_packages(check_file_pkgs, db.db_id, store, full_resync)

            logger.debug(f"Processing already installed file packages '{db.db_id}'...")
            self._process_already_installed_packages(already_installed_pkgs)

            logger.debug(f"Processing validate file packages '{db.db_id}'...")
            fetch_pkgs.extend(self._process_validate_packages(validate_pkgs))

            logger.debug(f"Processing moved file packages '{db.db_id}'...")
            self._process_moved_packages(moved_pkgs, store)

            self._ctx.file_download_session_logger.print_header(db, nothing_to_download=len(fetch_pkgs) == 0)

            logger.debug(f"Reserving space '{db.db_id}'...")
            if not self._try_reserve_space(fetch_pkgs):
                logger.debug(f"Not enough space '{db.db_id}'!")
                return None, None # @TODO return error instead to retry later?

            logger.debug(f"Processing create folder packages '{db.db_id}'...")
            self._process_create_folder_packages(create_folder_pkgs, db, store)  # @TODO maybe move this one after reserve space

            logger.debug(f"Processing remove file packages '{db.db_id}'...")
            self._process_remove_file_packages(remove_files_pkgs, db.db_id)

            logger.debug(f"Processing delete folder packages '{db.db_id}'...")
            self._process_delete_folder_packages(delete_folder_pkgs, db.db_id)

            logger.debug(f"Process fetch packages and launch fetch jobs '{db.db_id}'...")
            next_jobs = self._process_fetch_packages_and_launch_jobs(fetch_pkgs, db.base_files_url)
            return next_jobs, None
        except BadFileFilterPartException as e:
            return None, e
        except StoragePriorityError as e:
            return None, e

    def _create_packages_from_index(self, config: Dict[str, Any], summary: Index, db: DbEntity, store: ReadOnlyStoreAdapter) -> Tuple[
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
        calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(config)

        check_file_pkgs: List[_CheckFilePackage] = self._translate_items(calculator, filtered_summary.files, PathType.FILE, {})
        remove_files_pkgs: List[_RemoveFilePackage] = self._translate_items(calculator, store.files, PathType.FILE, filtered_summary.files)

        # @TODO REFACTOR: This looks wrong
        # remove_files_pkgs = [pkg for pkg in remove_files_pkgs if 'zip_id' not in pkg.description]

        existing_folders: Dict[str, Any] = filtered_summary.folders.copy()
        for pkg in check_file_pkgs:
            path_obj = Path(pkg.rel_path)
            target_path_obj = Path(pkg.full_path)
            while len(path_obj.parts) > 1:
                path_obj = path_obj.parent
                target_path_obj = target_path_obj.parent
                path_str = ('|' if pkg.is_potentially_external else '') + str(path_obj)
                if path_str not in existing_folders:
                    existing_folders[path_str] = store.folders.get(path_str, {})

        create_folder_pkgs: List[_CreateFolderPackage] = self._translate_items(calculator, existing_folders, PathType.FOLDER, {})
        delete_folder_pkgs: List[_DeleteFolderPackage] = self._translate_items(calculator, store.folders, PathType.FOLDER, existing_folders)

        # @TODO REFACTOR: This looks wrong
        # delete_folder_pkgs = [pkg for pkg in delete_folder_pkgs if 'zip_id' not in pkg.description]

        # @TODO commenting these 2 lines make the test still pass, why?
        for pkg in check_file_pkgs:
            if pkg.rel_path is FILE_MiSTer: pkg.description['backup'] = FILE_MiSTer_old

        return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs

    @staticmethod
    def _translate_items(calculator: TargetPathsCalculator, items: Dict[str, Dict[str, Any]], path_type: PathType, exclude_items: Dict[str, Any]) -> List[PathPackage]:
        # @TODO: This should be optimized, calling deduce target path twice should be unnecessary.
        exclude = set()
        for path, description in exclude_items.items():
            exclude.add(calculator.deduce_target_path(path, description, path_type).rel_path)

        translated = []
        for path, description in items.items():
            pkg = calculator.deduce_target_path(path, description, path_type)
            if pkg.rel_path in exclude:
                continue

            translated.append(pkg)

        return translated

    def _process_check_file_packages(self, check_file_pkgs: List[_CheckFilePackage], db_id: str, store: ReadOnlyStoreAdapter, full_resync: bool) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage], List[_MovedFilePackage], List[_AlreadyInstalledFilePackage]]:
        if len(check_file_pkgs) == 0:
            return [], [], [], []

        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        non_duplicated_pkgs: List[_CheckFilePackage] = []
        duplicated_files = []
        with self._ctx.top_lock:
            for pkg in check_file_pkgs:
                # @TODO Should check a collection instead of a single file to minimize lock time
                if self._ctx.installation_report.is_file_processed(pkg.rel_path):
                    duplicated_files.append(pkg.rel_path)
                else:
                    # @TODO Should add a collection instead of a single file to minimize lock time
                    self._ctx.installation_report.add_processed_file(pkg, db_id)
                    non_duplicated_pkgs.append(pkg)

        for file_path in duplicated_files:
            self._ctx.file_download_session_logger.print_progress_line(f'DUPLICATED: {file_path} [using {self._ctx.installation_report.processed_file(file_path).db_id} instead]')

        fetch_pkgs: List[_FetchFilePackage] = []
        validate_pkgs: List[_ValidateFilePackage] = []
        moved_pkgs: List[_ValidateFilePackage] = []
        already_installed_pkgs: List[_ValidateFilePackage] = []
        for pkg in non_duplicated_pkgs:
            if file_system.is_file(pkg.full_path):
                if not full_resync and store.hash_file(pkg.rel_path) == pkg.description['hash']:
                    if store.is_file_in_drive(pkg.rel_path, pkg.drive()):
                        already_installed_pkgs.append(pkg)
                    else:
                        validate_pkgs.append(pkg)
                        moved_pkgs.append(pkg)
                else:
                    validate_pkgs.append(pkg)
            else:
                fetch_pkgs.append(pkg)

        return fetch_pkgs, validate_pkgs, moved_pkgs, already_installed_pkgs

    def _process_already_installed_packages(self, already_installed_pkgs: List[_AlreadyInstalledFilePackage]) -> None:
        if len(already_installed_pkgs) == 0:
            return

        already_installed_files: List[str] = [pkg.rel_path for pkg in already_installed_pkgs]
        with self._ctx.top_lock:
            self._ctx.installation_report.add_present_not_validated_files(already_installed_files)

    def _process_validate_packages(self, validate_pkgs: List[_ValidateFilePackage]) -> List[_FetchFilePackage]:
        if len(validate_pkgs) == 0:
            return []

        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        more_fetch_pkgs: List[_FetchFilePackage] = []
        present_validated_files: List[str] = []
        skipped_updated_files: List[str] = []

        for pkg in validate_pkgs:
            # @TODO: Parallelize the slow hash calculations
            if file_system.hash(pkg.full_path) == pkg.description['hash']:
                self._ctx.file_download_session_logger.print_progress_line(f'No changes: {pkg.rel_path}')
                present_validated_files.append(pkg.rel_path)
                continue

            if 'overwrite' in pkg.description and not pkg.description['overwrite']:
                if file_system.hash(pkg.full_path) != pkg.description['hash']:
                    skipped_updated_files.append(pkg.rel_path)
                else:
                    present_validated_files.append(pkg.rel_path)

                continue

            more_fetch_pkgs.append(pkg)

        if len(present_validated_files) > 0:
            with self._ctx.top_lock:
                self._ctx.installation_report.add_present_validated_files(present_validated_files)

        if len(skipped_updated_files) > 0:
            with self._ctx.top_lock:
                self._ctx.installation_report.add_skipped_updated_files(skipped_updated_files)

        return more_fetch_pkgs

    def _process_moved_packages(self, moved_pkgs: List[_MovedFilePackage], store: ReadOnlyStoreAdapter) -> None:
        if len(moved_pkgs) == 0:
            return

        moved_files: List[Tuple[bool, str, str, PathType]] = []
        for pkg in moved_pkgs:
            for is_external, other_drive in store.list_other_drives_for_file(pkg.rel_path, pkg.drive()):
                other_file = os.path.join(other_drive, pkg.rel_path)
                if not self._ctx.file_system.is_file(other_file):
                    moved_files.append((is_external, pkg.rel_path, other_drive, PathType.FILE))

        if len(moved_files) == 0:
            return

        with self._ctx.top_lock:
            self._ctx.installation_report.add_removed_copies(moved_files)

    def _try_reserve_space(self, fetch_pkgs: List[_FetchFilePackage]) -> bool:
        if len(fetch_pkgs) == 0:
            return True

        with self._ctx.top_lock:
            fits_well, full_partitions = self._ctx.free_space_reservation.reserve_space_for_file_pkgs(fetch_pkgs)
        if fits_well:
            return True
        else:
            for partition, _ in full_partitions:
                self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")
            with self._ctx.top_lock:
                # @TODO Should use a report lock instead of the top lock
                for partition, failed_reserve in full_partitions:
                    # @TODO Should add a collection instead of a single file to minimize lock time
                    self._ctx.installation_report.add_full_partition(partition, failed_reserve)

                for pkg in fetch_pkgs:
                    # @TODO Should add a collection instead of a single file to minimize lock time
                    self._ctx.installation_report.add_failed_file(pkg.rel_path)
                #    self._ctx.free_space_reservation.release_space_for_file(pkg.full_path, pkg.description)

            return False

    def _process_create_folder_packages(self, create_folder_pkgs: List[_CreateFolderPackage], db: DbEntity, store: ReadOnlyStoreAdapter):
        if len(create_folder_pkgs) == 0:
            return

        folders_to_create: Set[str] = set()
        folder_copies_to_be_removed: List[Tuple[bool, str, str, PathType]] = []
        parents: Dict[str, Set[str]] = defaultdict(set)

        for pkg in create_folder_pkgs:
            if pkg.is_pext_parent:
                continue

            if pkg.pext_props:
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

        with self._ctx.top_lock:
            self._ctx.installation_report.add_removed_copies(folder_copies_to_be_removed)
            for pkg in create_folder_pkgs:
                if pkg.db_path() not in db.folders: continue

                # @TODO Why two adds?
                # @TODO Should add a collection instead of a single file to minimize lock time
                self._ctx.installation_report.add_processed_folder(pkg, db.db_id)
                self._ctx.installation_report.add_installed_folder(pkg.rel_path)

    def _maybe_add_copies_to_remove(self, copies: List[Tuple[bool, str, str, PathType]], store: ReadOnlyStoreAdapter, folder_path: str, drive: Optional[str]):
        if store.folder_drive(folder_path) == drive: return
        copies.extend([
            (is_external, folder_path, other_drive, PathType.FOLDER)
            for is_external, other_drive in store.list_other_drives_for_folder(folder_path, drive)
            if not self._ctx.file_system.is_folder(os.path.join(other_drive, folder_path))
        ])

    def _process_remove_file_packages(self, remove_files_pkgs: List[_RemoveFilePackage], db_id: str):
        if len(remove_files_pkgs) == 0:
            return

        with self._ctx.top_lock:
            for pkg in remove_files_pkgs:
                # @TODO Should queue a collection instead of a single file to minimize lock time
                self._ctx.pending_removals.queue_file_removal(pkg, db_id)

    def _process_delete_folder_packages(self, delete_folder_pkgs: List[_DeleteFolderPackage], db_id: str):
        if len(delete_folder_pkgs) == 0:
            return

        with self._ctx.top_lock:
            for pkg in delete_folder_pkgs:
                # @TODO Should queue a collection instead of a single file to minimize lock time
                self._ctx.pending_removals.queue_directory_removal(pkg, db_id)

    def _process_fetch_packages_and_launch_jobs(self, fetch_pkgs: List[_FetchFilePackage], base_files_url: str) -> List[Job]:
        if len(fetch_pkgs) == 0:
            return []

        jobs = []
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
