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
    K_BASE_SYSTEM_PATH, PathType
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.local_store_wrapper import StoreWrapper
from downloader.online_importer import WrongDatabaseOptions
from downloader.other import calculate_url
from downloader.storage_priority_resolver import StoragePriorityRegistryEntry, StoragePriorityError


class ProcessDbWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = threading.Lock()
        self._processed_files: Dict[str, str] = dict()
        self._full_partitions: Set[str] = set()
        self._correctly_installed_files: List[str] = []

    def initialize(self): self._ctx.job_system.register_worker(ProcessDbJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ProcessDbJob):
        self._ctx.file_download_reporter.print_header(job.db)
        db_config = self._build_db_config(self._ctx.config, job.db, job.ini_description)
        file_jobs = self._process_db(db_config, job.db, job.store, job.full_resync)
        if len(file_jobs) == 0:
            self._ctx.logger.print("Nothing new to download from given sources.")

        for target_file_path, file_path, file_description in file_jobs:
            url = file_description['url'] if 'url' in file_description else calculate_url(job.db.base_files_url, file_path if file_path[0] != '|' else file_path[1:])
            fetch_job = FetchFileJob2(url=url, info=file_path, download_path=target_file_path, silent=False)
            fetch_job.after_job = ValidateFileJob2(target_file_path=target_file_path, description=file_description, info=file_path, fetch_job=fetch_job)
            self._ctx.job_system.push_job(fetch_job)

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

    def _process_db(self, config: Dict[str, Any], db: DbEntity, store: StoreWrapper, full_resync: bool) -> List[Tuple[str, str, Dict[str, Any]]]:
        read_only_store = store.read_only()
        logger = self._ctx.logger

        if not read_only_store.has_base_path():
            store.write_only().set_base_path(config[K_BASE_PATH])

        logger.debug(f"Preparing db '{db.db_id}'...")
        file_system = ReadOnlyFileSystem(self._ctx.file_system)

        logger.bench('Filtering Database...')
        file_filter = self._create_file_filter(db, config)
        filtered_db, filtered_zip_data = file_filter.select_filtered_files(db)

        drives = list(self._ctx.external_drives_repository.connected_drives_except_base_path_drives(config))

        logger.bench('Translating paths...')
        priority_top_folders = {}
        folder_jobs = dict()
        for folder_path, folder_description in filtered_db.folders.items():
            target_folder_path = self._deduce_target_path(config, drives, priority_top_folders, folder_path, folder_description, PathType.FOLDER)
            folder_jobs[target_folder_path] = (folder_path, folder_description)

        candidate_file_jobs = []
        for file_path, file_description in filtered_db.files.items():
            target_file_path = self._deduce_target_path(config, drives, priority_top_folders, file_path, file_description, PathType.FILE)
            candidate_file_jobs.append((target_file_path, file_path, file_description))

        logger.bench('Selecting changed files...')

        with self._lock:
            for target_file_path, file_path, file_description in candidate_file_jobs:
                if file_path in self._processed_files:
                    logger.print('DUPLICATED: %s' % file_path)
                    logger.print('Already been processed by database: %s' % self._processed_files[file_path])
                else:
                    self._processed_files[file_path] = db.db_id

        file_jobs = []
        for target_file_path, file_path, file_description in candidate_file_jobs:
            if file_system.is_file(target_file_path):
                store_hash = read_only_store.hash_file(file_path)

                if not full_resync and store_hash == file_description['hash']:
                    store.write_only().add_file(file_path, file_description)
                    continue

                if store_hash == 'file_does_not_exist_so_cant_get_hash' and file_system.hash(target_file_path) == file_description['hash']:
                    store.write_only().add_file(file_path, file_description)
                    logger.print('No changes: %s' % file_path)
                    self._correctly_installed_files.append(file_path)
                    continue

                if 'overwrite' in file_description and not file_description['overwrite']:
                    if file_system.hash(target_file_path) != file_description['hash']:
                        with self._lock:
                            store.write_only().add_new_file_not_overwritten(db.db_id, file_path)
                    continue

            file_jobs.append((target_file_path, file_path, file_description))

        with self._lock:
            for target_file_path, _, file_description in file_jobs:
                self._ctx.free_space_reservation.reserve_space_for_file(target_file_path, file_description)

            logger.debug(f"Free space: {self._ctx.free_space_reservation.free_space()}")
            full_partitions = self._ctx.free_space_reservation.get_full_partitions()
            if len(full_partitions) > 0:
                for partition in full_partitions:
                    logger.print(f"Partition {partition.partition_path} would get full!")
                    self._full_partitions.add(partition.partition_path)

                for target_file_path, _, file_description in file_jobs:
                    self._ctx.free_space_reservation.release_space_for_file(target_file_path, file_description)

                return []

        for target_folder_path, (folder_path, folder_description) in folder_jobs.items():
            self._ctx.file_system.make_dirs(target_folder_path)
            store.write_only().add_folder(folder_path, folder_description)

        return file_jobs

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
        try:
            return FileFilterFactory(self._ctx.logger).create(db, config)
        except BadFileFilterPartException as e:
            raise WrongDatabaseOptions("Wrong custom download filter on database %s. Part '%s' is invalid." % (db.db_id, str(e)))

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
