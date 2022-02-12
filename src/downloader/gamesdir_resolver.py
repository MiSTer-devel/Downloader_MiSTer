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
from downloader.constants import GAMESDIR_PRIORITY, K_GAMESDIR_PATH
from downloader.other import cache


class GamesdirResolverFactory:
    def __init__(self, auto_path_resolver):
        self._auto_path_resolver = auto_path_resolver

    def create(self, config):
        return _GamesdirConfigResolver(config, self._auto_path_resolver)


class GamesdirAutoResolver:
    def __init__(self, file_system, logger):
        self._file_system = file_system
        self._logger = logger
        self._drive_folders_cache = {}

    def translate_auto_path(self, path):
        parts = path.split('/')
        if len(parts) <= 2:
            raise GamesdirError("Path '|%s' is incorrect, please contact the database maintainer." % path)

        auto_path = self._auto_path(parts[1])
        if auto_path is None:
            return path

        return '%s/%s' % (auto_path, path)

    def _auto_path(self, directory):
        for drive in self._gamesdir_priority():
            if self._is_directory_on_drive(drive, directory):
                return drive

        return None

    def _is_directory_on_drive(self, drive, directory):
        if drive not in self._drive_folders_cache:
            self._drive_folders_cache[drive] = {}

        if directory not in self._drive_folders_cache[drive]:
            self._drive_folders_cache[drive][directory] = self._check_if_folder_exists('%s/games/%s' % (drive, directory))
        return self._drive_folders_cache[drive][directory]

    @cache
    def _gamesdir_priority(self):
        result = []
        for drive in GAMESDIR_PRIORITY:
            if self._is_gamesdir_not_empty_on_drive('%s/games' % drive):
                result.append(drive)

        if len(result) > 0:
            self._logger.debug()
            self._logger.debug('Detected following connected drives:')
            for directory in result:
                self._logger.debug(directory)
            self._logger.debug()

        return result

    def _is_gamesdir_not_empty_on_drive(self, drive):
        return self._file_system.is_folder(drive) and self._file_system.folder_has_items(drive)

    def _check_if_folder_exists(self, folder):
        return self._file_system.is_folder(folder)


class _GamesdirConfigResolver:
    def __init__(self, config, auto_path_resolver):
        self._config = config
        self._auto_path_resolver = auto_path_resolver

    def translate_path(self, path):
        if path[0] != '|':
            return path

        path = path[1:]

        if not path.startswith('games/'):
            raise GamesdirError("Path '|%s' should not start with character '|', please contact the database maintainer." % path)

        if self._config[K_GAMESDIR_PATH] != 'auto':
            return '%s/%s' % (self._config[K_GAMESDIR_PATH], path)

        return self._auto_path_resolver.translate_auto_path(path)


class GamesdirError(Exception):
    pass
