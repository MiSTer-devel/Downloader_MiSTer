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

from typing import Dict, Any, List, Optional, Tuple
import os
import threading
from pathlib import Path

from downloader.config import Config
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.constants import K_STORAGE_PRIORITY, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL
from downloader.path_package import PathPackageKind, PextPathProps, PathPackage, PextKind, PathType
from downloader.storage_priority_resolver import StoragePriorityRegistryEntry, StoragePriorityError


class TargetPathsCalculatorFactory:
    def __init__(self, file_system: FileSystem, external_drives_repository: ExternalDrivesRepository):
        self._file_system = file_system
        self._external_drives_repository = external_drives_repository
        self._lock = threading.Lock()

    def target_paths_calculator(self, config: Config) -> 'TargetPathsCalculator':
        drives = list(self._external_drives_repository.connected_drives_except_base_path_drives(config))
        return TargetPathsCalculator(self._file_system, config, drives, self._lock)


class TargetPathsCalculator:
    def __init__(self, file_system: FileSystem, config: Config, drives: List[str], lock: threading.Lock):
        self._file_system = file_system
        self._config = config
        self._drives = drives
        self._lock = lock
        self._priority_top_folders: Dict[str, StoragePriorityRegistryEntry] = dict()

    def deduce_target_path(self, path: str, description: Dict[str, Any], path_type: PathType) -> PathPackage:
        is_system_file = 'path' in description and description['path'] == 'system'
        can_be_external = path[0] == '|'
        if is_system_file and can_be_external:
            raise StoragePriorityError(f"System Path '{path}' is incorrect because it starts with '|', please contact the database maintainer.")
        elif can_be_external:
            rel_path = path[1:]
            full_path, extra = self._deduce_possible_external_target_path(path=rel_path, path_type=path_type)
            return PathPackage(full_path, rel_path, description, path_type, PathPackageKind.PEXT, extra)
        elif is_system_file:
            return PathPackage(os.path.join(self._config['base_system_path'], path), path, description, path_type, PathPackageKind.SYSTEM, None)
        else:
            return PathPackage(os.path.join(self._config['base_path'], path), path, description, path_type, PathPackageKind.STANDARD, None)

    def _deduce_possible_external_target_path(self, path: str, path_type: PathType) -> Tuple[str, PextPathProps]:
        path_obj = Path(path)
        parts_len = len(path_obj.parts)
        if path_type == PathType.FOLDER and parts_len <= 1:
            return os.path.join(self._config['base_path'], path), PextPathProps(kind=PextKind.PEXT_PARENT, parent=path, drive=self._config['base_path'], other_drives=())
        elif path_type == PathType.FILE and parts_len <= 2:
            raise StoragePriorityError(f"File Path '|{path}' is incorrect, please contact the database maintainer.")
        else:
            return self._deduce_external_target_path_from_priority(source_path=path, path_obj=path_obj)

    def _deduce_external_target_path_from_priority(self, source_path: str, path_obj: Path) -> Tuple[str, PextPathProps]:
        first_folder, second_folder, *_ = path_obj.parts
        first_two_folders = '%s/%s' % (first_folder, second_folder)

        with self._lock:
            if first_folder not in self._priority_top_folders:
                self._priority_top_folders[first_folder] = StoragePriorityRegistryEntry()

            registry = self._priority_top_folders[first_folder]

            if first_two_folders not in registry.folders:
                drive, external, others = self._search_drive_for_directory(first_folder, second_folder)
                registry.folders[first_two_folders] = (drive, external, others)
                registry.drives.add(drive)

        drive, external, others = registry.folders[first_two_folders]
        return os.path.join(drive, source_path), PextPathProps(kind=external, parent=first_folder, drive=drive, other_drives=others, is_subfolder=len(path_obj.parts) == 2)

    def _search_drive_for_directory(self, first_folder: str, second_folder: str) -> Tuple[str, PextKind, Tuple[str, ...]]:
        base_path, priority = self._config['base_path'], self._config['storage_priority']

        if priority == STORAGE_PRIORITY_OFF:
            return base_path, PextKind.PEXT_STANDARD, ()
        elif priority == STORAGE_PRIORITY_PREFER_SD:
            result, others = self._first_drive_with_existing_directory_prefer_sd(os.path.join(first_folder, second_folder))
            if result is not None:
                return result, PextKind.PEXT_EXTERNAL, others

            return base_path, PextKind.PEXT_STANDARD, ()
        elif priority == STORAGE_PRIORITY_PREFER_EXTERNAL:
            # Check better_test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations
            #   and better_test_download_external_drives_1_and_2___on_store_and_fs____installs_at_expected_locations
            #   They should be the actual behavior instead of the legacy behavior we are using right now. We'll need to fix it in a later release
            #   where the following code would be uncommented and these tests would replace the current passing test.
            #
            # result, others = self._first_drive_with_existing_directory_prefer_external(first_folder)
            # if result is not None:
            #    return result, PextKind.PEXT_EXTERNAL, others

            if len(self._drives):
                return self._drives[0], PextKind.PEXT_EXTERNAL, ()
            else:
                return base_path, PextKind.PEXT_STANDARD, ()
        else:
            raise StoragePriorityError('%s "%s" not valid!' % (K_STORAGE_PRIORITY, priority))

    def _first_drive_with_existing_directory_prefer_sd(self, directory: str) -> Tuple[Optional[str], Tuple[str, ...]]:
        result = None
        others = None
        for drive in self._drives:
            absolute_directory = os.path.join(drive, directory)
            if self._file_system.is_folder(absolute_directory):
                if result is None:
                    result = drive
                elif others is None:
                    others = [drive]
                else:
                    others.append(drive)

        return result, tuple(others) if others is not None else ()

    def _first_drive_with_existing_directory_prefer_external(self, directory: str) -> Tuple[Optional[str], Tuple[str, ...]]:
        result = None
        others = None
        for drive in self._drives:
            absolute_directory = os.path.join(drive, directory)
            if self._file_system.is_folder(absolute_directory):
                if result is None:
                    result = drive
                elif others is None:
                    others = [drive]
                else:
                    others.append(drive)

        if result is None and len(self._drives) > 0:
            result = self._drives[0]
            if len(self._drives) > 1:
                others = self._drives[1:]

        return result, tuple(others) if others is not None else ()