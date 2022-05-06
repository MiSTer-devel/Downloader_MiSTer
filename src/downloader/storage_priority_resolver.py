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
from pathlib import Path

from downloader.constants import K_STORAGE_PRIORITY, K_BASE_PATH, PathType
from downloader.other import UnreachableException


class StoragePriorityResolver:
    def __init__(self, file_system_factory, external_drives_repository):
        self._file_system_factory = file_system_factory
        self._external_drives_repository = external_drives_repository

    def create(self, config, priority_top_folders):
        drives = list(self._external_drives_repository.connected_drives_except_base_path_drives(config))
        return _StoragePriorityResolver(config, self._external_drives_repository, self._file_system_factory.create_for_system_scope(), drives, priority_top_folders)


class StoragePriorityRegistryEntry:
    def __init__(self):
        self.drives = set()
        self.folders = dict()


class _StoragePriorityResolver:
    def __init__(self, config, external_drives_repository, system_file_system, drives, priority_top_folders):
        self._config = config
        self._external_drives_repository = external_drives_repository
        self._system_file_system = system_file_system
        self._drives = drives
        self._priority_top_folders = priority_top_folders

    def resolve_storage_priority(self, path, path_type):
        if path[0] == '|':
            raise StoragePriorityError("Path '|%s' is incorrect, please contact the database maintainer." % path)

        parts = Path(path).parts
        if path_type is PathType.FOLDER:
            if len(parts) <= 1:
                return self._config[K_BASE_PATH]

        elif path_type is PathType.FILE:
            if len(parts) <= 2:
                raise StoragePriorityError("File Path '|%s' is incorrect, please contact the database maintainer." % path)
        else:
            raise UnreachableException('path_type can not be "%s" for path %s' % (str(path_type), path))

        return self._resolve_from_drives((parts[0], parts[1]))

    def _resolve_from_drives(self, directory_tuple):
        first, second = directory_tuple
        if first not in self._priority_top_folders:
            self._priority_top_folders[first] = StoragePriorityRegistryEntry()
        if second not in self._priority_top_folders[first].folders:
            drive = self._search_drive_for_directory('%s/%s' % (first, second))
            self._priority_top_folders[first].folders[second] = drive
            self._priority_top_folders[first].drives.add(drive)
        return self._priority_top_folders[first].folders[second]

    def _search_drive_for_directory(self, directory):
        if self._config[K_STORAGE_PRIORITY] == 'off':
            return self._config[K_BASE_PATH]
        elif self._config[K_STORAGE_PRIORITY] == 'prefer_sd':
            result = self._first_drive_with_existing_directory(directory)
            if result is not None:
                return result

            return self._config[K_BASE_PATH]
        elif self._config[K_STORAGE_PRIORITY] == 'prefer_external':
            result = self._first_drive_with_existing_directory(directory)
            if result is not None:
                return result

            return self._drives[0] if len(self._drives) else self._config[K_BASE_PATH]
        elif self._system_file_system.is_folder(self._config[K_STORAGE_PRIORITY]):
            return self._config[K_STORAGE_PRIORITY]
        else:
            raise StoragePriorityError('%s "%s" not valid!' % (K_STORAGE_PRIORITY, self._config[K_STORAGE_PRIORITY]))

    def _first_drive_with_existing_directory(self, directory):
        for drive in self._drives:
            absolute_directory = '%s/%s' % (drive, directory)
            if self._system_file_system.is_folder(absolute_directory):
                return drive

        return None


class StoragePriorityError(Exception):
    pass
