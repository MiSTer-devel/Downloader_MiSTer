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

from downloader.config import AllowReboot
from downloader.constants import FILE_mister_downloader_needs_reboot, K_ALLOW_REBOOT


class RebootCalculator:
    def __init__(self, config, logger, file_system):
        self._config = config
        self._logger = logger
        self._file_system = file_system

    def calc_needs_reboot(self, linux_needs_reboot, importer_needs_reboot):

        will_reboot = False
        should_reboot = False

        if self._config[K_ALLOW_REBOOT] == AllowReboot.NEVER:
            should_reboot = linux_needs_reboot or importer_needs_reboot
        elif self._config[K_ALLOW_REBOOT] == AllowReboot.ONLY_AFTER_LINUX_UPDATE:
            will_reboot = linux_needs_reboot
            should_reboot = importer_needs_reboot
        elif self._config[K_ALLOW_REBOOT] == AllowReboot.ALWAYS:
            will_reboot = linux_needs_reboot or importer_needs_reboot
        else:
            raise Exception('AllowReboot.%s not recognized' % AllowReboot.name)

        if will_reboot:
            return True

        if should_reboot:
            self._file_system.touch(FILE_mister_downloader_needs_reboot)
            if linux_needs_reboot:
                self._logger.print('Linux has been updated! It is recommended to reboot your system now.')
            else:
                self._logger.print('Reboot MiSTer to apply some changes.')
            self._logger.print()

        return False
