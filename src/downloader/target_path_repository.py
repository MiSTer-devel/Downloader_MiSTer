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

from downloader.constants import FILE_MiSTer, FILE_MiSTer_new


downloader_in_progress_postfix = '._downloader_in_progress'


class TargetPathRepository:
    def __init__(self, config, file_system):
        self._config = config
        self._file_system = file_system
        self._registry = {}
        self._tempfiles = {}
        self._file_mister = None
        self._file_mister_new = None

    def create_target(self, path, description):
        path, skips_registry = self._fix_path(path)
        if skips_registry:
            return path

        target_path = self._calculate_target_path(path, description)
        self._registry[path] = target_path
        return target_path

    def _calculate_target_path(self, path, description):
        if not self._file_system.is_file(path):
            return path

        if description['size'] <= 5000000:
            unique_temp_filename = self._file_system.unique_temp_filename()
            target_path = unique_temp_filename.value
            self._tempfiles[target_path] = unique_temp_filename
            return target_path

        return path + downloader_in_progress_postfix

    def access_target(self, path):
        path, skips_registry = self._fix_path(path)
        if skips_registry:
            return path

        return self._registry[path]

    def clean_target(self, path):
        path, skips_registry = self._fix_path(path)
        if skips_registry:
            self._file_system.unlink(path)
            return

        target_path = self._registry[path]
        self._file_system.unlink(target_path)
        self._registry.pop(path)
        if target_path in self._tempfiles:
            self._tempfiles[target_path].close()
            self._tempfiles.pop(target_path)

    def finish_target(self, path):
        path, skips_registry = self._fix_path(path)
        if skips_registry:
            return

        target_path = self._registry[path]
        if target_path != path:
            self._file_system.copy(target_path, path)
            self._file_system.unlink(target_path)
        self._registry.pop(path)

    def _fix_path(self, path):
        fixed_path = path if path != FILE_MiSTer else FILE_MiSTer_new
        target_path = self._file_system.download_target_path(fixed_path)
        return target_path, fixed_path == target_path
