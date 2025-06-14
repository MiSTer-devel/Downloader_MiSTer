# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from typing import Protocol, Any

from downloader.error import DownloaderError
from downloader.logger import Logger


class StoreMigrator:
    def __init__(self, migration_list: list['MigrationBase'], logger: Logger) -> None:
        self._migrations = migration_list
        self._logger = logger

    def migrate(self, local_store: dict[str, Any]) -> None:
        self._logger.bench('Migration start.')

        current_version = local_store.get('migration_version', 0)
        if current_version >= len(self._migrations):
            self._logger.bench('Migration not necessary, early return.')
            return

        for i in range(current_version, len(self._migrations), 1):
            if (self._migrations[i].version - 1) != i:
                raise WrongMigrationException('Migration error: (%s -1) != %s' % (self._migrations[i].version, i))

            self._logger.debug('Running migration version %s.' % self._migrations[i].version)
            self._migrations[i].migrate(local_store)

        local_store['migration_version'] = self.latest_migration_version()

        self._logger.bench('Migration done.')

    def latest_migration_version(self) -> int:
        return len(self._migrations)


def make_new_local_store(store_migrator) -> dict[str, Any]:
    return {
        'dbs': {},
        'db_sigs': {},
        'migration_version': store_migrator.latest_migration_version(),
        'internal': True
    }


class WrongMigrationException(DownloaderError):
    pass


class MigrationBase(Protocol):
    version: int
    def migrate(self, local_store) -> None: ...
