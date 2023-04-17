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
from typing import Dict, Any
from downloader.constants import K_OPTIONS, K_DEFAULT_DB_ID, K_BASE_PATH, K_USER_DEFINED_OPTIONS, K_FILTER


class ImporterCommand:
    def __init__(self, config: Dict[str, Any], user_defined_options):
        self._config = config
        self._user_defined_options = user_defined_options
        self._parameters = []

    def add_db(self, db, store, ini_description):
        config = self._config.copy()

        for key, option in db.default_options.items():
            if key not in self._user_defined_options or (key == K_FILTER and '[mister]' in option.lower()):
                config[key] = option

        if K_OPTIONS in ini_description:
            ini_description[K_OPTIONS].apply_to_config(config)

        if not store.read_only().has_base_path():
            store.write_only().set_base_path(config[K_BASE_PATH])

        if config[K_FILTER] is not None and '[mister]' in config[K_FILTER].lower():
            mister_filter = '' if K_FILTER not in self._config or self._config[K_FILTER] is None else self._config[K_FILTER].lower()
            config[K_FILTER] = config[K_FILTER].lower().replace('[mister]', mister_filter)

        entry = (db, store, config)

        if db.db_id == self._config[K_DEFAULT_DB_ID]:
            self._parameters = [entry, *self._parameters]
        else:
            self._parameters.append(entry)

        return self

    def read_dbs(self):
        return self._parameters


class ImporterCommandFactory:
    def __init__(self, config):
        self._config = config

    def create(self) -> ImporterCommand:
        return ImporterCommand(self._config, self._config[K_USER_DEFINED_OPTIONS])
