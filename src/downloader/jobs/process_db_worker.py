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
import os
from pathlib import Path
import threading

from downloader.db_entity import DbEntity
from downloader.file_filter import BadFileFilterPartException, FileFilterFactory
from downloader.file_system import ReadOnlyFileSystem
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.constants import K_USER_DEFINED_OPTIONS, K_FILTER, K_OPTIONS, K_BASE_PATH, K_STORAGE_PRIORITY, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    K_BASE_SYSTEM_PATH, PathType, FILE_MiSTer, FILE_MiSTer_old
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.local_store_wrapper import StoreWrapper, NO_HASH_IN_STORE_CODE
from downloader.online_importer import WrongDatabaseOptions
from downloader.other import calculate_url
from downloader.storage_priority_resolver import StoragePriorityRegistryEntry, StoragePriorityError


_Desc = Dict[str, Any]
_Path = str
_TargetPath = str
_ItemTuple = Tuple[_TargetPath, _Path, _Desc]
_CheckFilePackage = _ItemTuple
_FetchFilePackage = _ItemTuple
_ValidateFilePackage = _ItemTuple
_RemoveFilePackage = _ItemTuple
_CreateFolderPackage = _ItemTuple
_DeleteFolderPackage = _ItemTuple


class ProcessDbWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = threading.Lock()
        self._full_partitions: Set[str] = set()

    def initialize(self): self._ctx.job_system.register_worker(ProcessDbJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ProcessDbJob):
        logger = self._ctx.logger
        db_id = job.db.db_id
        base_files_url = job.db.base_files_url

        logger.debug(f"Building db config '{db_id}'...")
        db_config = self._build_db_config(self._ctx.config, job.db, job.ini_description)

        logger.debug(f"Processing db '{db_id}'...")
        check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs = self._process_db(db_config, job.db, job.store)

        logger.debug(f"Processing check file packages '{db_id}'...")
        fetch_pkgs, validate_pkgs = self._process_check_file_packages(check_file_pkgs, db_id, job.store, job.full_resync)

        logger.debug(f"Processing validate file packages '{db_id}'...")
        fetch_pkgs.extend(self._process_validate_packages(validate_pkgs, job.store))

        self._ctx.file_download_reporter.print_header(job.db, nothing_to_download=len(fetch_pkgs) == 0)

        logger.debug(f"Reserving space '{db_id}'...")
        if not self._try_reserve_space(fetch_pkgs):
            logger.debug(f"Not enough space '{db_id}'!")
            return

        logger.debug(f"Processing create folder packages '{db_id}'...")
        self._process_create_folder_packages(create_folder_pkgs, job.store)

        logger.debug(f"Processing remove file packages '{db_id}'...")
        self._process_remove_file_packages(remove_files_pkgs, db_id)

        logger.debug(f"Processing delete folder packages '{db_id}'...")
        self._process_delete_folder_packages(delete_folder_pkgs, job.store)

        logger.debug(f"Launching fetch jobs '{db_id}'...")
        for target_file_path, file_path, file_description in fetch_pkgs:
            fetch_job = FetchFileJob2(url=self._url(file_path, file_description, base_files_url), info=file_path, download_path=target_file_path + '.new', silent=False)
            fetch_job.after_job = ValidateFileJob2(target_file_path=target_file_path, description=file_description, info=file_path, fetch_job=fetch_job)
            self._ctx.job_system.push_job(fetch_job)

    def _url(self, file_path: str, file_description: _Desc, base_files_url: str):
        return file_description['url'] if 'url' in file_description else calculate_url(base_files_url, file_path if file_path[0] != '|' else file_path[1:])

    @staticmethod
    def _build_db_config(input_config: Dict[str, Any], db: DbEntity, ini_description: Dict[str, Any]) -> Dict[str, Any]:
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

    def _process_db(self, config: Dict[str, Any], db: DbEntity, store: StoreWrapper) -> Tuple[
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
        file_filter = self._create_file_filter(db, config)
        filtered_db, filtered_zip_data = file_filter.select_filtered_files(db)

        logger.bench('Translating paths...')
        priority_top_folders = {}
        drives = list(self._ctx.external_drives_repository.connected_drives_except_base_path_drives(config))

        def translate_items(items: Dict[str, Dict[str, Any]], path_type: PathType, exclude_items: Dict[str, Any]) -> List[_ItemTuple]: return [(
            self._deduce_target_path(config, drives, priority_top_folders, path, description, path_type),
            path,
            description
        ) for path, description in items.items() if path not in exclude_items]

        check_file_pkgs: List[_CheckFilePackage] = translate_items(filtered_db.files, PathType.FILE, {})
        remove_files_pkgs: List[_RemoveFilePackage] = translate_items(read_only_store.files, PathType.FILE, filtered_db.files)

        existing_folders = filtered_db.folders.copy()
        for target_file_path, file_path, file_description in check_file_pkgs:
            path_obj = Path(file_path)
            target_path_obj = Path(target_file_path)
            while len(path_obj.parts) > 1:
                path_obj = path_obj.parent
                target_path_obj = target_path_obj.parent
                path_str = str(path_obj)
                if path_str not in existing_folders:
                    existing_folders[path_str] = read_only_store.folders.get(path_str, {})
                    self._ctx.file_system.make_dirs(str(target_path_obj))

        create_folder_pkgs: List[_CreateFolderPackage] = translate_items(filtered_db.folders, PathType.FOLDER, {})
        delete_folder_pkgs: List[_DeleteFolderPackage] = translate_items(read_only_store.folders, PathType.FOLDER, existing_folders)

        for target_file_path, file_path, file_description in check_file_pkgs:
            if file_path is FILE_MiSTer: file_description['backup'] = FILE_MiSTer_old

        return check_file_pkgs, remove_files_pkgs, create_folder_pkgs, delete_folder_pkgs

    def _deduce_target_path(self, config: Dict[str, Any], drives: List[str], priority_top_folders: Dict[str, StoragePriorityRegistryEntry], path: str, description: Dict[str, Any], path_type: PathType) -> str:
        is_system_file = 'path' in description and description['path'] == 'system'
        can_be_external = path[0] == '|'
        if is_system_file and can_be_external:
            raise StoragePriorityError(f"System Path '{path}' is incorrect because it starts with '|', please contact the database maintainer.")
        elif can_be_external:
            parts_len = len(Path(path).parts)
            if path_type == PathType.FOLDER and parts_len <= 1:
                return os.path.join(config[K_BASE_PATH], path[1:])
            elif path_type == PathType.FILE and parts_len <= 2:
                raise StoragePriorityError(f"File Path '{path}' is incorrect, please contact the database maintainer.")
            else:
                return self._deduce_target_path_from_priority(drives, priority_top_folders, config[K_STORAGE_PRIORITY], config[K_BASE_PATH], path[1:])
        elif is_system_file:
            return os.path.join(config[K_BASE_SYSTEM_PATH], path)
        else:
            return os.path.join(config[K_BASE_PATH], path)

    def _deduce_target_path_from_priority(self, drives: List[str], priority_top_folders: Dict[str, StoragePriorityRegistryEntry], priority: str, base_path: str, source_path: str) -> str:
        first_folder, second_folder, *_ = Path(source_path).parts
        if first_folder not in priority_top_folders:
            priority_top_folders[first_folder] = StoragePriorityRegistryEntry()
        if second_folder not in priority_top_folders[first_folder].folders:
            drive = self._search_drive_for_directory(drives, base_path, priority, os.path.join(first_folder, second_folder))
            priority_top_folders[first_folder].folders[second_folder] = drive
            priority_top_folders[first_folder].drives.add(drive)

        return os.path.join(priority_top_folders[first_folder].folders[second_folder], source_path)

    def _create_file_filter(self, db, config):
        return FileFilterFactory(self._ctx.logger).create(db, config)

    def _search_drive_for_directory(self, drives, base_path, priority, directory):
        if priority == STORAGE_PRIORITY_OFF:
            return base_path
        elif priority == STORAGE_PRIORITY_PREFER_SD:
            result = self._first_drive_with_existing_directory(drives, directory)
            if result is not None:
                return result

            return base_path
        elif priority == STORAGE_PRIORITY_PREFER_EXTERNAL:
            result = self._first_drive_with_existing_directory(drives, directory)
            if result is not None:
                return result

            return drives[0] if len(drives) else base_path
        else:
            raise StoragePriorityError('%s "%s" not valid!' % (K_STORAGE_PRIORITY, priority))

    def _first_drive_with_existing_directory(self, drives, directory):
        for drive in drives:
            absolute_directory = os.path.join(drive, directory)
            if self._ctx.file_system.is_folder(absolute_directory):
                return drive

        return None

    def _process_check_file_packages(self, check_file_pkgs: List[_CheckFilePackage], db_id: str, store: StoreWrapper, full_resync: bool) -> Tuple[List[_FetchFilePackage], List[_ValidateFilePackage]]:
        read_only_store = store.read_only()
        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        non_duplicated_pkgs: List[_CheckFilePackage] = []
        duplicated_files = []
        with self._lock:
            for target_file_path, file_path, file_description in check_file_pkgs:
                if self._ctx.installation_report.is_file_processed(file_path):
                    duplicated_files.append(file_path)
                else:
                    self._ctx.installation_report.add_processed_file(target_file_path, file_path, file_description, db_id)
                    non_duplicated_pkgs.append((target_file_path, file_path, file_description))

        for file_path in duplicated_files:
            self._ctx.file_download_reporter.print_progress_line(f'DUPLICATED: {file_path} [using {self._ctx.installation_report.processed_file(file_path).db_id} instead]')

        fetch_pkgs: List[_FetchFilePackage] = []
        validate_pkgs: List[_ValidateFilePackage] = []
        for target_file_path, file_path, file_description in non_duplicated_pkgs:
            if file_system.is_file(target_file_path):
                if not full_resync and read_only_store.hash_file(file_path) == file_description['hash']:
                    continue

                validate_pkgs.append((target_file_path, file_path, file_description))
            else:
                fetch_pkgs.append((target_file_path, file_path, file_description))

        return fetch_pkgs, validate_pkgs

    def _process_validate_packages(self, validate_pkgs: List[_ValidateFilePackage], store: StoreWrapper) -> List[_FetchFilePackage]:
        read_only_store = store.read_only()
        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        more_fetch_pkgs: List[_FetchFilePackage] = []

        for target_file_path, file_path, file_description in validate_pkgs:
            # @TODO: Parallelize the slow hash calculations
            if read_only_store.hash_file(file_path) == NO_HASH_IN_STORE_CODE and file_system.hash(target_file_path) == file_description['hash']:
                with self._lock:
                    self._ctx.file_download_reporter.print_progress_line(f'No changes: {file_path}')
                    self._ctx.installation_report.add_already_present_file(file_path)
                continue

            if 'overwrite' in file_description and not file_description['overwrite']:
                if file_system.hash(target_file_path) != file_description['hash']:
                    with self._lock:
                        self._ctx.installation_report.add_skipped_updated_file(file_path)
                continue

            more_fetch_pkgs.append((target_file_path, file_path, file_description))

        return more_fetch_pkgs

    def _process_remove_file_packages(self, remove_files_pkgs: List[_RemoveFilePackage], db_id: str):
        for target_file_path, _, _ in remove_files_pkgs:
            self._ctx.file_system.unlink(target_file_path)

        with self._lock:
            for target_file_path, file_path, file_description in remove_files_pkgs:
                self._ctx.installation_report.add_processed_file(target_file_path, file_path, file_description, db_id)
                self._ctx.installation_report.add_removed_file(file_path)

    def _process_delete_folder_packages(self, delete_folder_pkgs: List[_DeleteFolderPackage], store: StoreWrapper):
        for target_folder_path, folder_path, folder_description in delete_folder_pkgs:
            store.write_only().remove_folder(folder_path)
            self._ctx.file_system.remove_folder(target_folder_path)

    def _process_create_folder_packages(self, create_folder_pkgs: List[_CreateFolderPackage], store: StoreWrapper):
        for target_folder_path, folder_path, folder_description in create_folder_pkgs:
            self._ctx.file_system.make_dirs(target_folder_path)
            store.write_only().add_folder(folder_path, folder_description)

    def _try_reserve_space(self, fetch_pkgs: List[_FetchFilePackage]) -> bool:
        with self._lock:
            for target_file_path, _, file_description in fetch_pkgs:
                self._ctx.free_space_reservation.reserve_space_for_file(target_file_path, file_description)

            self._ctx.logger.debug(f"Free space: {self._ctx.free_space_reservation.free_space()}")
            full_partitions = self._ctx.free_space_reservation.get_full_partitions()
            if len(full_partitions) > 0:
                for partition in full_partitions:
                    self._ctx.file_download_reporter.print_progress_line(f"Partition {partition.partition_path} would get full!")
                    self._full_partitions.add(partition.partition_path)

                for target_file_path, _, file_description in fetch_pkgs:
                    self._ctx.free_space_reservation.release_space_for_file(target_file_path, file_description)

                return False

        return True