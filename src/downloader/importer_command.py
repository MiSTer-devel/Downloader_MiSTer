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
from typing import Tuple, List

from downloader.config import Config, ConfigDatabaseSection


class ImporterCommand:
    def __init__(self, default_db_id: str):
        self._default_db_id = default_db_id
        self._parameters: List[Tuple[str, ConfigDatabaseSection]] = []

    def add_db(self, db_id: str, ini_description: ConfigDatabaseSection):
        entry = (db_id, ini_description)
        if db_id == self._default_db_id:
            self._parameters = [entry, *self._parameters]
        else:
            self._parameters.append(entry)

        return self

    def read_dbs(self) -> List[Tuple[str, ConfigDatabaseSection]]:
        return self._parameters


class ImporterCommandFactory:
    def __init__(self, config: Config):
        self._config = config

    def create(self) -> ImporterCommand:
        return ImporterCommand(self._config['default_db_id'])
