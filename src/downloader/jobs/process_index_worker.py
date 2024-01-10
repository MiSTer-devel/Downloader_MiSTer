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

from typing import Dict, Any, List, Set, Tuple
from pathlib import Path
import threading

from downloader.db_entity import DbEntity
from downloader.file_filter import FileFilterFactory
from downloader.file_system import ReadOnlyFileSystem
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.path_package import PathPackage
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.index import Index
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.constants import K_BASE_PATH, PathType, FILE_MiSTer, FILE_MiSTer_old
from downloader.local_store_wrapper import StoreWrapper, NO_HASH_IN_STORE_CODE
from downloader.other import calculate_url

_CheckFilePackage = PathPackage
_FetchFilePackage = PathPackage
_ValidateFilePackage = PathPackage
_RemoveFilePackage = PathPackage
_CreateFolderPackage = PathPackage
_DeleteFolderPackage = PathPackage


class ProcessIndexWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = threading.Lock()
        self._full_partitions: Set[str] = set()

    def initialize(self): self._ctx.job_system.register_worker(ProcessIndexJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ProcessIndexJob):
        logger = self._ctx.logger
        db, config, summary, store, full_resync = job.db, job.config, job.index, job.store, job.full_resync
        base_files_url = job.db.base_files_url

        logger.debug(f"Processing db '{db.db_id}'...")
        check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs = self._process_index(config, summary, db, store)

        logger.debug(f"Processing check file packages '{db.db_id}'...")
        fetch_pkgs, validate_pkgs = self._process_check_file_packages(check_file_pkgs, db.db_id, store, full_resync)

        logger.debug(f"Processing validate file packages '{db.db_id}'...")
        fetch_pkgs.extend(self._process_validate_packages(validate_pkgs, store))

        self._ctx.file_download_reporter.print_header(db, nothing_to_download=len(fetch_pkgs) == 0)

        logger.debug(f"Reserving space '{db.db_id}'...")
        if not self._try_reserve_space(fetch_pkgs):
            logger.debug(f"Not enough space '{db.db_id}'!")
            return

        logger.debug(f"Processing create folder packages '{db.db_id}'...")
        self._process_create_folder_packages(create_folder_pkgs, store)

        logger.debug(f"Processing remove file packages '{db.db_id}'...")
        self._process_remove_file_packages(remove_files_pkgs, db.db_id)

        logger.debug(f"Processing delete folder packages '{db.db_id}'...")
        self._process_delete_folder_packages(delete_folder_pkgs, store)

        logger.debug(f"Launching fetch jobs '{db.db_id}'...")
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
            self._ctx.job_system.push_job(fetch_job)

    def _process_index(self, config: Dict[str, Any], summary: Index, db: DbEntity, store: StoreWrapper) -> Tuple[
        List[_CheckFilePackage],
        List[_RemoveFilePackage],
        List[_CreateFolderPackage],
        List[_DeleteFolderPackage]
    ]:
        read_only_store = store.read_only()
        logger = self._ctx.logger

        if not read_only_store.has_base_path():
            store.write_only().set_base_path(config[K_BASE_PATH])

        logger.bench('Filtering Database...')
        filtered_summary, _ = FileFilterFactory(self._ctx.logger)\
            .create(db, config)\
            .select_filtered_files(summary)

        logger.bench('Translating paths...')
        target_paths_calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(config)

        def translate_items(items: Dict[str, Dict[str, Any]], path_type: PathType, exclude_items: Dict[str, Any]) -> List[PathPackage]: return [PathPackage(
            full_path=target_paths_calculator.deduce_target_path(path, description, path_type),
            rel_path=path,
            description=description
        ) for path, description in items.items() if path not in exclude_items]

        check_file_pkgs: List[_CheckFilePackage] = translate_items(filtered_summary.files, PathType.FILE, {})
        remove_files_pkgs: List[_RemoveFilePackage] = translate_items(read_only_store.files, PathType.FILE, filtered_summary.files)

        # @REFACTOR: This looks wrong
        remove_files_pkgs = [pkg for pkg in remove_files_pkgs if 'zip_id' not in pkg.description]

        existing_folders = filtered_summary.folders.copy()
        for pkg in check_file_pkgs:
            path_obj = Path(pkg.rel_path)
            target_path_obj = Path(pkg.full_path)
            while len(path_obj.parts) > 1:
                path_obj = path_obj.parent
                target_path_obj = target_path_obj.parent
                path_str = str(path_obj)
                if path_str not in existing_folders:
                    existing_folders[path_str] = read_only_store.folders.get(path_str, {})
                    self._ctx.file_system.make_dirs(str(target_path_obj))

        create_folder_pkgs: List[_CreateFolderPackage] = translate_items(filtered_summary.folders, PathType.FOLDER, {})
        delete_folder_pkgs: List[_DeleteFolderPackage] = translate_items(read_only_store.folders, PathType.FOLDER, existing_folders)

        # @REFACTOR: This looks wrong
        delete_folder_pkgs = [pkg for pkg in delete_folder_pkgs if 'zip_id' not in pkg.description]

        # @TODO commenting these 2 lines make the test still pass, why?
        for pkg in check_file_pkgs:
            if pkg.rel_path is FILE_MiSTer: pkg.description['backup'] = FILE_MiSTer_old

        return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs

    def _process_check_file_packages(self, check_file_pkgs: List[_CheckFilePackage], db_id: str, store: StoreWrapper, full_resync: bool) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage]]:
        read_only_store = store.read_only()
        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        non_duplicated_pkgs: List[_CheckFilePackage] = []
        duplicated_files = []
        with self._lock:
            for pkg in check_file_pkgs:
                if self._ctx.installation_report.is_file_processed(pkg.rel_path):
                    duplicated_files.append(pkg.rel_path)
                else:
                    self._ctx.installation_report.add_processed_file(pkg, db_id)
                    non_duplicated_pkgs.append(pkg)

        for file_path in duplicated_files:
            self._ctx.file_download_reporter.print_progress_line(f'DUPLICATED: {file_path} [using {self._ctx.installation_report.processed_file(file_path).db_id} instead]')

        fetch_pkgs: List[_FetchFilePackage] = []
        validate_pkgs: List[_ValidateFilePackage] = []
        for pkg in non_duplicated_pkgs:
            if file_system.is_file(pkg.full_path):
                if not full_resync and read_only_store.hash_file(pkg.rel_path) == pkg.description['hash']:
                    continue

                validate_pkgs.append(pkg)
            else:
                fetch_pkgs.append(pkg)

        return fetch_pkgs, validate_pkgs

    def _process_validate_packages(self, validate_pkgs: List[_ValidateFilePackage], store: StoreWrapper) -> List[_FetchFilePackage]:
        read_only_store = store.read_only()
        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        more_fetch_pkgs: List[_FetchFilePackage] = []

        for pkg in validate_pkgs:
            # @TODO: Parallelize the slow hash calculations
            if read_only_store.hash_file(pkg.rel_path) == NO_HASH_IN_STORE_CODE and file_system.hash(pkg.full_path) == pkg.description['hash']:
                with self._lock:
                    self._ctx.file_download_reporter.print_progress_line(f'No changes: {pkg.rel_path}')
                    self._ctx.installation_report.add_already_present_file(pkg.rel_path)
                continue

            if 'overwrite' in pkg.description and not pkg.description['overwrite']:
                if file_system.hash(pkg.full_path) != pkg.description['hash']:
                    with self._lock:
                        self._ctx.installation_report.add_skipped_updated_file(pkg.rel_path)
                continue

            more_fetch_pkgs.append(pkg)

        return more_fetch_pkgs

    def _process_remove_file_packages(self, remove_files_pkgs: List[_RemoveFilePackage], db_id: str):
        for pkg in remove_files_pkgs:
            self._ctx.file_system.unlink(pkg.full_path)

        with self._lock:
            for pkg in remove_files_pkgs:
                self._ctx.installation_report.add_processed_file(pkg, db_id)
                self._ctx.installation_report.add_removed_file(pkg.rel_path)

    def _process_delete_folder_packages(self, delete_folder_pkgs: List[_DeleteFolderPackage], store: StoreWrapper):
        for pkg in delete_folder_pkgs:
            store.write_only().remove_folder(pkg.rel_path)
            self._ctx.file_system.remove_folder(pkg.full_path)

    def _process_create_folder_packages(self, create_folder_pkgs: List[_CreateFolderPackage], store: StoreWrapper):
        for pkg in create_folder_pkgs:
            self._ctx.file_system.make_dirs(pkg.full_path)
            store.write_only().add_folder(pkg.rel_path, pkg.description)

    def _try_reserve_space(self, fetch_pkgs: List[_FetchFilePackage]) -> bool:
        with self._lock:
            for pkg in fetch_pkgs:
                self._ctx.free_space_reservation.reserve_space_for_file(pkg.full_path,  pkg.description)

            self._ctx.logger.debug(f"Free space: {self._ctx.free_space_reservation.free_space()}")
            full_partitions = self._ctx.free_space_reservation.get_full_partitions()
            if len(full_partitions) > 0:
                for partition in full_partitions:
                    self._ctx.file_download_reporter.print_progress_line(f"Partition {partition.partition_path} would get full!")
                    self._full_partitions.add(partition.partition_path)

                for pkg in fetch_pkgs:
                    self._ctx.free_space_reservation.release_space_for_file(pkg.full_path, pkg.description)

                return False

        return True


def _url(file_path: str, file_description: Dict[str, Any], base_files_url: str):
    return file_description['url'] if 'url' in file_description else calculate_url(base_files_url, file_path if file_path[0] != '|' else file_path[1:])
