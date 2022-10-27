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
import os

from downloader.constants import K_BASE_PATH, K_BASE_SYSTEM_PATH, PathType


class PathResolverFactory:
    def __init__(self, storage_priority_resolver_factory, path_dictionary, os_name=None):
        self._storage_priority_resolver_factory = storage_priority_resolver_factory
        self._path_dictionary = path_dictionary
        self._os_name = os.name if os_name is None else os_name
        self._system_paths = set()

    def create(self, config, storage_priority_top_folders):
        return _PathResolver(config, self._path_dictionary, self._system_paths, self._os_name, self._storage_priority_resolver_factory.create(config, storage_priority_top_folders))


class _PathResolver:
    def __init__(self, config, path_dictionary, system_paths, os_name, storage_priority_resolver):
        self._config = config
        self._path_dictionary = path_dictionary
        self._system_paths = system_paths
        self._storage_priority_resolver = storage_priority_resolver
        self._os_name = os_name

    def resolve_path(self, path, path_type):
        if self._os_name == 'nt' and path.startswith('C:\\'):
            return None

        if path[0] == '/' or path.startswith('C:\\'):
            return None

        if path[0] == '|':
            path = path[1:]
            base = self._storage_priority_resolver.resolve_storage_priority(path, path_type)
        elif path in self._system_paths:
            base = self._config[K_BASE_SYSTEM_PATH]
        else:
            return None

        if base == self._config[K_BASE_PATH]:
            return None

        self._path_dictionary[path.lower()] = base
        return base

    def resolve_folder_path(self, path):
        return self.resolve_path(path, PathType.FOLDER)

    def resolve_file_path(self, path):
        return self.resolve_path(path, PathType.FILE)

    def add_system_path(self, path):
        self._system_paths.add(path)
