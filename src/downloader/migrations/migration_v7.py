# Copyright (c) 2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from downloader.constants import K_BASE_PATH
from downloader.store_migrator import MigrationBase
from downloader.config import Config


class MigrationV7(MigrationBase):
    def __init__(self, config: Config) -> None:
        self._config = config

    version = 7

    def migrate(self, local_store) -> None:
        for store in local_store['dbs'].values():
            store[K_BASE_PATH] = self._config['base_path']
