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

from typing import Dict, Any, List
import os
from pathlib import Path

from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.constants import K_BASE_PATH, K_STORAGE_PRIORITY, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    K_BASE_SYSTEM_PATH, PathType
from downloader.storage_priority_resolver import StoragePriorityRegistryEntry, StoragePriorityError


class TargetPathsCalculator:
    def __init__(self, file_system: FileSystem, config: Dict[str, Any], drives: List[str]):
        self._file_system = file_system
        self._config = config
        self._drives = drives
        self._priority_top_folders: Dict[str, StoragePriorityRegistryEntry] = {}

    @staticmethod
    def create_target_paths_calculator(file_system: FileSystem, config: Dict[str, Any], external_drives_repository: ExternalDrivesRepository) -> 'TargetPathsCalculator':
        drives = list(external_drives_repository.connected_drives_except_base_path_drives(config))
        return TargetPathsCalculator(file_system, config, drives)

    def deduce_target_path(self, path: str, description: Dict[str, Any], path_type: PathType) -> str:
        is_system_file = 'path' in description and description['path'] == 'system'
        can_be_external = path[0] == '|'
        if is_system_file and can_be_external:
            raise StoragePriorityError(f"System Path '{path}' is incorrect because it starts with '|', please contact the database maintainer.")
        elif can_be_external:
            parts_len = len(Path(path).parts)
            if path_type == PathType.FOLDER and parts_len <= 1:
                return os.path.join(self._config[K_BASE_PATH], path[1:])
            elif path_type == PathType.FILE and parts_len <= 2:
                raise StoragePriorityError(f"File Path '{path}' is incorrect, please contact the database maintainer.")
            else:
                return self._deduce_target_path_from_priority(self._drives, self._priority_top_folders, self._config[K_STORAGE_PRIORITY], self._config[K_BASE_PATH], path[1:])
        elif is_system_file:
            return os.path.join(self._config[K_BASE_SYSTEM_PATH], path)
        else:
            return os.path.join(self._config[K_BASE_PATH], path)

    def _deduce_target_path_from_priority(self, drives: List[str], priority_top_folders: Dict[str, StoragePriorityRegistryEntry], priority: str, base_path: str, source_path: str) -> str:
        first_folder, second_folder, *_ = Path(source_path).parts
        if first_folder not in priority_top_folders:
            priority_top_folders[first_folder] = StoragePriorityRegistryEntry()
        if second_folder not in priority_top_folders[first_folder].folders:
            drive = self._search_drive_for_directory(drives, base_path, priority, os.path.join(first_folder, second_folder))
            priority_top_folders[first_folder].folders[second_folder] = drive
            priority_top_folders[first_folder].drives.add(drive)

        return os.path.join(priority_top_folders[first_folder].folders[second_folder], source_path)

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
            if self._file_system.is_folder(absolute_directory):
                return drive

        return None
