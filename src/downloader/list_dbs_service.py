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

import os
from pathlib import Path

from downloader.config import Config
from downloader.constants import FILE_downloader_run_signal, FILE_downloader_storage_fingerprints_json
from downloader.db_utils import sorted_db_sections
from downloader.file_system import FileSystem
from downloader.logger import Logger
from downloader.update_output import UpdateOutput


class ListDbsService:
    def __init__(self, update_output: UpdateOutput, file_system: FileSystem, logger: Logger) -> None:
        self._update_output = update_output
        self._file_system = file_system
        self._logger = logger

    def list_dbs(self, config: Config, db_filter: str = 'all') -> int:
        if db_filter in ('all', 'configured'):
            self._update_output.configured_databases(sorted_db_sections(config))
        if db_filter in ('all', 'installed'):
            self._update_output.installed_databases(self._installed_db_ids(config))
        self._remove_run_signal()
        return 0

    def _installed_db_ids(self, config: Config) -> list[str]:
        fingerprints_path = os.path.join(config['base_system_path'], FILE_downloader_storage_fingerprints_json)
        try:
            if not self._file_system.is_file(fingerprints_path):
                return []
            fingerprints = self._file_system.load_dict_from_file(fingerprints_path)
        except Exception as e:
            self._logger.debug(e)
            self._logger.print('WARNING: Could not load store fingerprints')
            return []
        if not isinstance(fingerprints, dict):
            return []
        return sorted(fingerprints.keys())

    @staticmethod
    def _remove_run_signal() -> None:
        try:
            Path(FILE_downloader_run_signal).unlink(missing_ok=True)
        except OSError:
            pass
