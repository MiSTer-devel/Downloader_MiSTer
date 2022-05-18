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
from downloader.config import default_config
from downloader.importer_command import ImporterCommand as ProductionImporterCommand
from test.fake_local_store_wrapper import LocalStoreWrapper


class ImporterCommand(ProductionImporterCommand):
    def __init__(self, input_config):
        user_defined_config = []
        for key, value in default_config().items():
            if key in input_config and value != input_config[key]:
                user_defined_config.append(key)

        super().__init__(input_config, user_defined_config)

    def add_db(self, db, local_store, ini_description):
        if isinstance(local_store, dict):
            return super().add_db(db, LocalStoreWrapper.from_store(db.db_id, local_store), ini_description)
        else:
            return super().add_db(db, local_store, ini_description)
