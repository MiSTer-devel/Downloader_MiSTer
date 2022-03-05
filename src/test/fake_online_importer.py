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
from downloader.file_filter import FileFilterFactory
from downloader.importer_command import ImporterCommand
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_logger import NoLogger


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, waiter=None, logger=None):
        self._config = config if config is not None else default_config()
        self._file_system_factory = FileSystemFactory.from_state(config=self._config) if file_system_factory is None else file_system_factory
        file_downloader_factory = FileDownloaderFactory(config=config, file_system_factory=self._file_system_factory) if file_downloader_factory is None else file_downloader_factory
        self.file_system = self._file_system_factory.create_for_system_scope()

        super().__init__(
            FileFilterFactory(),
            self._file_system_factory,
            file_downloader_factory,
            NoWaiter() if waiter is None else waiter,
            NoLogger() if logger is None else logger)

        self._importer_command = ImporterCommand(self._config, [])

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs):
        file_downloader_factory, file_system_factory, config = FileDownloaderFactory.from_implicit_inputs(implicit_inputs)

        return OnlineImporter(config=config, file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory)

    @property
    def fs_data(self):
        return self._file_system_factory.data

    def download(self, full_resync):
        self.download_dbs_contents(self._importer_command, full_resync)
        for _, store, _ in self._importer_command.read_dbs():
            self._clean_store(store)

        return self

    def add_db(self, db, store, description=None):
        self._importer_command.add_db(db, store, {} if description is None else description)
        return self

    def download_db(self, db, store, full_resync=False):
        self.add_db(db, store)
        self.download(full_resync)
        self._clean_store(store)
        return store

    @staticmethod
    def _clean_store(store):
        for zip_description in store['zips'].values():
            if 'zipped_files' in zip_description['contents_file']:
                zip_description['contents_file'].pop('zipped_files')
            if 'summary_file' in zip_description and 'unzipped_json' in zip_description['summary_file']:
                zip_description['summary_file'].pop('unzipped_json')
