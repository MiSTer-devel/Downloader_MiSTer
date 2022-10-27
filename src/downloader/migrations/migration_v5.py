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
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, K_DATABASES, K_OPTIONS
from downloader.store_migrator import MigrationBase


class MigrationV5(MigrationBase):
    def __init__(self, file_system_factory, path_resolver_factory, config):
        self._file_system_factory = file_system_factory
        self._path_resolver_factory = path_resolver_factory
        self._config = config

    version = 5

    def migrate(self, local_store):
        """remove old mister from old location in case it exists"""

        config = self._config.copy()
        try:
            ini_description = self._config[K_DATABASES][DISTRIBUTION_MISTER_DB_ID]
        except KeyError as _:
            return

        if K_OPTIONS in ini_description:
            ini_description[K_OPTIONS].apply_to_config(config)

        file_system = self._file_system_factory.create_for_config(config)

        storage_priority_top_folders = {}

        migrate_file_mister_old(file_system, self._path_resolver_factory.create(config, storage_priority_top_folders))


def migrate_file_mister_old(file_system, path_resolver):
    file_MiSTer_old = 'Scripts/.config/downloader/MiSTer.old'

    path_resolver.add_system_path(file_MiSTer_old)
    path_resolver.resolve_file_path(file_MiSTer_old)

    if file_system.is_file(file_MiSTer_old):
        file_system.unlink(file_MiSTer_old)
