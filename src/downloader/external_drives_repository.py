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
from downloader.constants import STORAGE_PATHS_PRIORITY_SEQUENCE, MEDIA_FAT, K_BASE_SYSTEM_PATH, K_BASE_PATH
from downloader.other import cache


class ExternalDrivesRepositoryFactory:
    def create(self, file_system, logger):
        return ExternalDrivesRepository(file_system, logger)


class ExternalDrivesRepository:
    def __init__(self, file_system, logger):
        self._file_system = file_system
        self._logger = logger
        self._drive_folders_cache = {}

    @cache
    def connected_drives(self):
        result = self._retrieve_connected_drives_list()
        if len(result) > 0:
            self._logger.debug()
            self._logger.debug('Detected following connected drives:')
            for directory in result:
                self._logger.debug(directory)
            self._logger.debug()
        return result

    def connected_drives_except_base_path_drives(self, config):
        blocklist = set()
        if K_BASE_SYSTEM_PATH in config:
            blocklist.add(config[K_BASE_SYSTEM_PATH])
        if K_BASE_PATH in config:
            blocklist.add(config[K_BASE_PATH])
        return (drive for drive in self.connected_drives() if drive not in blocklist)

    def _retrieve_connected_drives_list(self):
        try:
            return self._drives_from_os()
        except Exception as e:
            self._logger.debug(e)
            return self._drives_from_fs()

    def _drives_from_os(self):
        connected_drives = set()
        for line in self._file_system.read_file_contents('/proc/mounts').splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split(' ')
            if len(parts) < 2:
                continue

            mount_point = parts[1]
            if mount_point.startswith('/media/usb') or mount_point.startswith('/media/fat/cifs'):
                connected_drives.add(mount_point)

        return tuple(drive for drive in STORAGE_PATHS_PRIORITY_SEQUENCE if drive in connected_drives)

    def _drives_from_fs(self):
        result = []
        for drive in STORAGE_PATHS_PRIORITY_SEQUENCE:
            if drive is MEDIA_FAT:
                continue

            if self._file_system.is_folder(drive):
                result.append(drive)

        return tuple(result)
