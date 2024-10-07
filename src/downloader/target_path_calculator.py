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

from typing import Dict, Any, List, Optional, Tuple, TypedDict
from enum import unique, Enum
import os
import threading
from pathlib import Path

from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.constants import K_BASE_PATH, K_STORAGE_PRIORITY, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    K_BASE_SYSTEM_PATH, PathType
from downloader.storage_priority_resolver import StoragePriorityRegistryEntry, StoragePriorityError


@unique
class TargetPathType(Enum):
    STANDARD = 0
    SYSTEM = 1
    RELATIVE_EXTERNAL = 2
    RELATIVE_STANDARD = 3
    RELATIVE_PARENT = 4


class PathExtra(TypedDict):
    parent: str
    drive: str


class TargetPathsCalculatorFactory:
    def __init__(self, file_system: FileSystem, external_drives_repository: ExternalDrivesRepository):
        self._file_system = file_system
        self._external_drives_repository = external_drives_repository
        self._lock = threading.Lock()

    def target_paths_calculator(self, config: Dict[str, Any]) -> 'TargetPathsCalculator':
        drives = list(self._external_drives_repository.connected_drives_except_base_path_drives(config))
        return TargetPathsCalculator(self._file_system, config, drives, self._lock)


class TargetPathsCalculator:
    def __init__(self, file_system: FileSystem, config: Dict[str, Any], drives: List[str], lock: threading.Lock):
        self._file_system = file_system
        self._config = config
        self._drives = drives
        self._lock = lock
        self._priority_top_folders: Dict[str, StoragePriorityRegistryEntry] = dict()

    def deduce_target_path(self, path: str, description: Dict[str, Any], path_type: PathType) -> Tuple[str, str, TargetPathType, Optional[PathExtra]]:
        is_system_file = 'path' in description and description['path'] == 'system'
        can_be_external = path[0] == '|'
        if is_system_file and can_be_external:
            raise StoragePriorityError(f"System Path '{path}' is incorrect because it starts with '|', please contact the database maintainer.")
        elif can_be_external:
            rel_path = path[1:]
            full_path, ty, extra = self._deduce_possible_external_target_path(path=rel_path, path_type=path_type)
            return full_path, rel_path, ty, extra
        elif is_system_file:
            return os.path.join(self._config[K_BASE_SYSTEM_PATH], path), path, TargetPathType.SYSTEM, None
        else:
            return os.path.join(self._config[K_BASE_PATH], path), path, TargetPathType.STANDARD, None

    def _deduce_possible_external_target_path(self, path: str, path_type: PathType) -> Tuple[str, TargetPathType, PathExtra]:
        parts_len = len(Path(path).parts)
        if path_type == PathType.FOLDER and parts_len <= 1:
            return os.path.join(self._config[K_BASE_PATH], path), TargetPathType.RELATIVE_PARENT, PathExtra(parent=path, drive=self._config[K_BASE_PATH])
        elif path_type == PathType.FILE and parts_len <= 2:
            raise StoragePriorityError(f"File Path '|{path}' is incorrect, please contact the database maintainer.")
        else:
            return self._deduce_external_target_path_from_priority(source_path=path)

    def _deduce_external_target_path_from_priority(self, source_path: str) -> Tuple[str, TargetPathType, PathExtra]:
        first_folder, second_folder, *_ = Path(source_path).parts
        first_two_folders = '%s/%s' % (first_folder, second_folder)

        with self._lock:
            if first_folder not in self._priority_top_folders:
                self._priority_top_folders[first_folder] = StoragePriorityRegistryEntry()

            registry = self._priority_top_folders[first_folder]

            if first_two_folders not in registry.folders:
                drive, external = self._search_drive_for_directory(directory=os.path.join(first_folder, second_folder))
                registry.folders[first_two_folders] = (drive, external)
                registry.drives.add(drive)

        drive, external = registry.folders[first_two_folders]
        return os.path.join(drive, source_path), external, PathExtra(parent=first_folder, drive=drive)

    def _search_drive_for_directory(self, directory: str) -> Tuple[str, TargetPathType]:
        base_path, priority = self._config[K_BASE_PATH], self._config[K_STORAGE_PRIORITY]

        if priority == STORAGE_PRIORITY_OFF:
            return base_path, TargetPathType.RELATIVE_STANDARD
        elif priority == STORAGE_PRIORITY_PREFER_SD:
            result = self._first_drive_with_existing_directory(directory)
            if result is not None:
                return result, TargetPathType.RELATIVE_EXTERNAL

            return base_path, TargetPathType.RELATIVE_STANDARD
        elif priority == STORAGE_PRIORITY_PREFER_EXTERNAL:
            result = self._first_drive_with_existing_directory(directory)
            if result is not None:
                return result, TargetPathType.RELATIVE_EXTERNAL

            if len(self._drives):
                return self._drives[0], TargetPathType.RELATIVE_EXTERNAL
            else:
                return base_path, TargetPathType.RELATIVE_STANDARD
        else:
            raise StoragePriorityError('%s "%s" not valid!' % (K_STORAGE_PRIORITY, priority))

    def _first_drive_with_existing_directory(self, directory: str) -> Optional[str]:
        for drive in self._drives:
            absolute_directory = os.path.join(drive, directory)
            if self._file_system.is_folder(absolute_directory):
                return drive

        return None
