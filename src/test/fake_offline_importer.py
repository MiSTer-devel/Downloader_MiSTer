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
from test.fake_importer_command import ImporterCommand
from test.fake_local_store_wrapper import StoreWrapper
from downloader.offline_importer import OfflineImporter as ProductionOfflineImporter
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory
from downloader.logger import NoLogger


class OfflineImporter(ProductionOfflineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None):
        self._config = default_config() if config is None else config
        self._file_system_factory = FileSystemFactory.from_state(config=config) if file_system_factory is None else file_system_factory
        file_downloader_factory = FileDownloaderFactory(config=self._config, file_system_factory=file_system_factory) if file_downloader_factory is None else file_downloader_factory
        self.file_system = self._file_system_factory.create_for_config(self._config)
        self._importer_command = ImporterCommand(self._config)
        super().__init__(
            self._file_system_factory,
            file_downloader_factory,
            NoLogger())

    @staticmethod
    def from_implicit_inputs(implicit_inputs):
        file_downloader_factory, file_system_factory, config = FileDownloaderFactory.from_implicit_inputs(implicit_inputs)

        return OfflineImporter(config=config, file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory)

    @property
    def fs_data(self):
        return self._file_system_factory.data

    def apply(self):
        self.apply_offline_databases(self._importer_command)
        return self

    def add_db(self, db, store, description=None):
        self._importer_command.add_db(db, store, {} if description is None else description)
        return self
