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
from downloader.db_gateway import DbGateway as ProductionDbGateway
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory
from downloader.logger import NoLogger


class DbGateway(ProductionDbGateway):
    def __init__(self, config=None, file_system_factory=None, file_downloader_factory=None):
        self._config = default_config() if config is None else config
        self._file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        self.file_system = self._file_system_factory.create_for_system_scope()
        super().__init__(
            self._config,
            self.file_system,
            FileDownloaderFactory(file_system_factory=self._file_system_factory) if file_downloader_factory is None else file_downloader_factory,
            NoLogger())

    @staticmethod
    def with_single_db(db_id, descr, config=None) -> ProductionDbGateway:
        state = FileSystemState(config=config, files={db_id: {'unzipped_json': descr}})
        db_gateway = DbGateway(config=config, file_system_factory=FileSystemFactory(state=state))
        return db_gateway
