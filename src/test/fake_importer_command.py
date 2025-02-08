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
from downloader.importer_command import ImporterCommand as ProductionImporterCommand
from downloader.local_store_wrapper import StoreWrapper
from test.fake_local_store_wrapper import StoreWrapper as FakeStoreWrapper


class ImporterCommand(ProductionImporterCommand):
    def add_db(self, db, store, ini_description):
        if isinstance(store, StoreWrapper):
            return super().add_db(db, store, ini_description)
        else:
            return super().add_db(db, FakeStoreWrapper(store), ini_description)
