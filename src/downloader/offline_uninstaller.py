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
from downloader.local_repository import LocalRepository
from downloader.logger import Logger
from downloader.update_output import UpdateOutput
from downloader.waiter import Waiter


class OfflineUninstaller:
    def __init__(self, config: Config, file_system: FileSystem, local_repository: LocalRepository, waiter: Waiter, update_output: UpdateOutput, logger: Logger) -> None:
        self._config = config
        self._file_system = file_system
        self._local_repository = local_repository
        self._waiter = waiter
        self._update_output = update_output
        self._logger = logger

    def uninstall_dbs(self, db_ids: list[str], force: bool) -> 'UninstallBox':
        raise NotImplementedError('GREEN phase pending')


class UninstallBox:
    def __init__(self) -> None:
        self._invalid_db_ids: list[str] = []
        self._refused_dbs: list[tuple[str, str]] = []
        self._failed_db_ids: list[str] = []
        self._uninstalled_db_ids: list[str] = []
        self._save_failed: bool = False
        self._removed_bytes: int = 0
        self._removed_files: int = 0

    def add_invalid_db_id(self, db_id: str) -> None:
        self._invalid_db_ids.append(db_id)

    def add_refused_db(self, db_id: str, reason: str) -> None:
        self._refused_dbs.append((db_id, reason))

    def add_failed_db(self, db_id: str) -> None:
        self._failed_db_ids.append(db_id)

    def add_uninstalled_db(self, db_id: str) -> None:
        self._uninstalled_db_ids.append(db_id)

    def add_removed_file(self, size: int) -> None:
        self._removed_files += 1
        self._removed_bytes += size

    def set_save_failed(self) -> None:
        self._save_failed = True

    def invalid_db_ids(self) -> list[str]: return list(self._invalid_db_ids)
    def refused_db_ids(self) -> list[str]: return [db_id for db_id, _reason in self._refused_dbs]
    def failed_db_ids(self) -> list[str]: return list(self._failed_db_ids)
    def uninstalled_db_ids(self) -> list[str]: return list(self._uninstalled_db_ids)
    def save_failed(self) -> bool: return self._save_failed
    def removed_bytes(self) -> int: return self._removed_bytes
    def removed_files(self) -> int: return self._removed_files
