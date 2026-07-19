# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.config import Config
from downloader.file_system import FileSystem
from downloader.logger import Logger
from downloader.offline_uninstaller import OfflineUninstaller
from downloader.update_output import UpdateOutput


class UninstallService:
    def __init__(self, config: Config, offline_uninstaller: OfflineUninstaller, file_system: FileSystem, update_output: UpdateOutput, logger: Logger) -> None:
        self._config = config
        self._offline_uninstaller = offline_uninstaller
        self._file_system = file_system
        self._update_output = update_output
        self._logger = logger

    def uninstall(self, db_ids: list[str], force: bool = False) -> int:
        raise NotImplementedError('GREEN phase pending')
