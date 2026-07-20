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

import re
from dataclasses import dataclass
from enum import Enum, unique
from typing import Optional

from downloader.config import Config
from downloader.file_system import FileSystem
from downloader.ini_section_remover import remove_ini_section


@unique
class DatabaseReappearanceReason(Enum):
    NO_SOURCE = 'no_source'
    NO_DATABASES_IN_BASE_INI = 'no_databases_in_base_ini'


@dataclass(frozen=True)
class DatabaseConfigRemovalFailure:
    source: str
    error: Exception


@dataclass(frozen=True)
class DatabaseConfigRemovalResult:
    failures: tuple[DatabaseConfigRemovalFailure, ...] = ()
    reappearance_reason: Optional[DatabaseReappearanceReason] = None


class DatabaseConfigRemover:
    def __init__(self, config: Config, file_system: FileSystem) -> None:
        self._config = config
        self._file_system = file_system

    def remove(self, db_id: str) -> DatabaseConfigRemovalResult:
        sources = self._source_files(db_id)
        configured = any(
            key.lower() == db_id.lower()
            for key in self._config['databases']
        )
        if not sources:
            reason = (
                DatabaseReappearanceReason.NO_SOURCE
                if configured
                else None
            )
            return DatabaseConfigRemovalResult(reappearance_reason=reason)

        failures: list[DatabaseConfigRemovalFailure] = []
        base_ini = str(self._config['config_path'])
        removed_from_base = False
        updated_base_content: bytes = b''
        for source in sources:
            if not self._file_system.is_file(source):
                continue
            try:
                original = self._file_system.read_file_bytes(source).getvalue()
                updated, found = remove_ini_section(original, db_id)
            except Exception as error:
                failures.append(DatabaseConfigRemovalFailure(source, error))
                continue
            if not found:
                continue
            if source == base_ini:
                removed_from_base = True
                updated_base_content = updated
            if source != base_ini and not updated.strip():
                write_error = self._file_system.unlink(source, verbose=False)
            else:
                write_error = self._file_system.write_file_bytes_atomically(
                    source, updated)
            if write_error is not None:
                failures.append(
                    DatabaseConfigRemovalFailure(source, write_error))

        reason = None
        if (
                not failures
                and removed_from_base
                and not self._base_ini_has_other_database(
                    updated_base_content, db_id)
        ):
            reason = DatabaseReappearanceReason.NO_DATABASES_IN_BASE_INI
        return DatabaseConfigRemovalResult(tuple(failures), reason)

    def _source_files(self, db_id: str) -> list[str]:
        files: list[str] = []
        for source_db_id, path in self._config.get(
                'database_sources', {}).items():
            if source_db_id.lower() == db_id.lower() and path not in files:
                files.append(path)
        for ignored in self._config['ignored_databases']:
            ignored_db_id = ignored.get('db_id')
            if (
                    isinstance(ignored_db_id, str)
                    and ignored_db_id.lower() == db_id.lower()
            ):
                path = ignored['file']
                if path not in files:
                    files.append(path)
        return files

    def _base_ini_has_other_database(
            self,
            content: bytes,
            removed_db_id: str,
    ) -> bool:
        base_ini = str(self._config['config_path'])
        configured = {
            db_id.lower()
            for db_id in self._config['databases']
        }
        sources = {
            db_id.lower(): source
            for db_id, source in self._config.get(
                'database_sources', {}).items()
        }
        for section in re.findall(
                rb'^[ \t]*\[([^\]\r\n]+)\]', content, re.MULTILINE):
            section_id = section.decode('utf-8').strip().lower()
            if (
                    section_id == 'mister'
                    or section_id == removed_db_id.lower()
            ):
                continue
            if (
                    section_id not in configured
                    or sources.get(section_id) == base_ini
            ):
                return True
        return False
