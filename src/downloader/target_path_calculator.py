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

from typing import ItemsView, Dict, Any, List, Optional, Tuple, Union
import os
import threading
from pathlib import Path

from downloader.config import Config
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.constants import K_STORAGE_PRIORITY, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL
from downloader.path_package import PATH_PACKAGE_KIND_PEXT, PATH_PACKAGE_KIND_STANDARD, PATH_PACKAGE_KIND_SYSTEM, PATH_TYPE_FILE, PATH_TYPE_FOLDER, PEXT_KIND_EXTERNAL, PEXT_KIND_PARENT, PEXT_KIND_STANDARD, PextPathProps, PathPackage, PextKind, PathType



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

    def deduce_target_path(self, path: str, description: Dict[str, Any], path_type: PathType) -> Tuple[PathPackage, Optional['StoragePriorityError']]:
        result, errors = self.create_path_packages([(path, description)], path_type)
        return result[0], errors[0] if len(errors) > 0 else None

    def create_path_packages(self, packages: Union[ItemsView[str, dict[str, Any]], list[Tuple[str, dict[str, Any]]]], ty: PathType, /) -> Tuple[list[PathPackage], list['StoragePriorityError']]:
        errors: list[StoragePriorityError] = []

        new = object.__new__
        cls = PathPackage

        # This weird obj creation is an optimization, since python 3.9 works much faster this way than with a traditional loop + traditional object initialization and this is part is super hot for perf
        result_pkgs = [new(cls) for _ in range(len(packages))]

        base_path = self._config['base_path']
        for (path, description), pkg in zip(packages, result_pkgs):
            pkg.rel_path = path
            pkg.description = description
            pkg.ty = ty
            if path[0] == '/':
                pkg._full_path = path
                pkg.drive = None
                pkg.kind = PATH_PACKAGE_KIND_STANDARD
                pkg.pext_props = None
                continue

            pkg._full_path = None
            is_system_file = 'path' in description and description['path'] == 'system'
            can_be_external = path[0] == '|'
            if can_be_external:
                pkg.rel_path = path[1:]
                external, error = self._deduce_possible_external_target_path(path=pkg.rel_path, path_type=pkg.ty)
                if error is not None:
                    pkg.drive = base_path
                    pkg.kind = PATH_PACKAGE_KIND_STANDARD
                    pkg.pext_props = None
                    errors.append(error)
                    continue

                pkg.drive, pkg.pext_props = external
                pkg.kind = PATH_PACKAGE_KIND_PEXT

                if is_system_file:
                    errors.append(StoragePriorityError(f"System Path '{path}' is incorrect because it starts with '|', please contact the database maintainer."))
                    continue

            elif is_system_file:
                pkg.drive = self._config['base_system_path']
                pkg.kind = PATH_PACKAGE_KIND_SYSTEM
                pkg.pext_props = None
            else:
                pkg.drive = base_path
                pkg.kind = PATH_PACKAGE_KIND_STANDARD
                pkg.pext_props = None

        return result_pkgs, errors

    def _deduce_possible_external_target_path(self, path: str, path_type: PathType) -> Tuple[Optional[Tuple[str, PextPathProps]], Optional['StoragePriorityError']]:
        path_obj = Path(path)
        parts_len = len(path_obj.parts)
        if path_type == PATH_TYPE_FOLDER and parts_len <= 1:
            return (self._config['base_path'], PextPathProps(
                PEXT_KIND_PARENT,  # kind
                path,  # parent
                self._config['base_path'],  # drive
                (),  # other_drives
                False  # is_subfolder
            )), None
        elif path_type == PATH_TYPE_FILE and parts_len <= 2:
            return None, StoragePriorityError(f"File Path '|{path}' is incorrect, please contact the database maintainer.")
        else:
            return self._deduce_external_target_path_from_priority(source_path=path, path_obj=path_obj), None

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
        return drive, PextPathProps(
            external,  # kind
            first_folder,  # parent
            drive,  # drive
            others,  # other_drives
            len(path_obj.parts) == 2,  # is_subfolder
        )

    def _search_drive_for_directory(self, first_folder: str, second_folder: str) -> Tuple[str, PextKind, Tuple[str, ...]]:
        base_path, priority = self._config['base_path'], self._config['storage_priority']

        if priority == STORAGE_PRIORITY_OFF:
            return base_path, PEXT_KIND_STANDARD, ()
        elif priority == STORAGE_PRIORITY_PREFER_SD:
            result, others = self._first_drive_with_existing_directory_prefer_sd(os.path.join(first_folder, second_folder))
            if result is not None:
                return result, PEXT_KIND_EXTERNAL, others

            return base_path, PEXT_KIND_STANDARD, ()
        elif priority == STORAGE_PRIORITY_PREFER_EXTERNAL:
            # Check better_test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations
            #   and better_test_download_external_drives_1_and_2___on_store_and_fs____installs_at_expected_locations
            #   They should be the actual behavior instead of the legacy behavior we are using right now. We'll need to fix it in a later release
            #   where the following code would be uncommented and these tests would replace the current passing test.
            #
            result, others = self._first_drive_with_existing_directory_prefer_sd(os.path.join(first_folder, second_folder))
            if result is not None:
               return result, PEXT_KIND_EXTERNAL, others

            result, others = self._first_external_alternative()
            if result is not None:
                return result, PEXT_KIND_EXTERNAL, others

            return base_path, PEXT_KIND_STANDARD, ()
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

    def _first_external_alternative(self) -> Tuple[Optional[str], Tuple[str, ...]]:
        result = None
        others = None

        if len(self._drives) > 0:
            result = self._drives[0]
            if len(self._drives) > 1:
                others = tuple(self._drives[1:])

        return result, () if others is None else others


class StoragePriorityError(Exception): pass

class StoragePriorityRegistryEntry:
    def __init__(self):
        self.drives = set()
        self.folders = dict()
