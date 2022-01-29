# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

class ImporterCommand:
    def __init__(self, config, user_defined_options):
        self._config = config
        self._user_defined_options = user_defined_options
        self._parameters = []

    def add_db(self, db, store, ini_description):
        config = self._config.copy()

        for key, option in db.default_options.items():
            if key not in self._user_defined_options:
                config[key] = option

        if 'options' in ini_description:
            ini_description['options'].apply_to_config(config)

        self._parameters.append((db, store, config))
        return self

    def read_dbs(self):
        return self._parameters
