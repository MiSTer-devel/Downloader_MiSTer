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
from downloader.constants import MEDIA_USB0
from downloader.file_filter import FileFilterFactory
from downloader.importer_command import ImporterCommand
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter
from test.fake_local_store_wrapper import StoreWrapper, LocalStoreWrapper
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_local_repository import LocalRepository
from test.fake_path_resolver import PathResolverFactory
from test.objects import config_with
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, FileSystemState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_logger import NoLogger


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, path_resolver_factory=None, local_repository=None, waiter=None, logger=None):
        self._config = config if config is not None else config_with(base_system_path=MEDIA_USB0)
        file_system_state = FileSystemState(config=self._config)
        self._file_system_factory = FileSystemFactory(state=file_system_state) if file_system_factory is None else file_system_factory
        file_downloader_factory = FileDownloaderFactory(config=config, file_system_factory=self._file_system_factory) if file_downloader_factory is None else file_downloader_factory
        self.file_system = self._file_system_factory.create_for_system_scope()
        path_resolver_factory = PathResolverFactory(path_dictionary=file_system_state.path_dictionary) if path_resolver_factory is None else path_resolver_factory

        self.needs_save = False

        super().__init__(
            FileFilterFactory(),
            self._file_system_factory,
            file_downloader_factory,
            path_resolver_factory,
            LocalRepository(config=self._config, file_system=self.file_system) if local_repository is None else local_repository,
            ExternalDrivesRepository(file_system=self.file_system),
            NoWaiter() if waiter is None else waiter,
            NoLogger() if logger is None else logger)

        self._importer_command = ImporterCommand(self._config, [])

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs):
        file_downloader_factory, file_system_factory, config = FileDownloaderFactory.from_implicit_inputs(implicit_inputs)

        path_resolver_factory = PathResolverFactory.from_file_system_state(implicit_inputs.file_system_state)

        return OnlineImporter(config=config, file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory, path_resolver_factory=path_resolver_factory)

    @property
    def fs_data(self):
        return self._file_system_factory.data

    @property
    def fs_records(self):
        return self._file_system_factory.records

    def download(self, full_resync):
        self.download_dbs_contents(self._importer_command, full_resync)
        for _, store, _ in self._importer_command.read_dbs():
            self._clean_store(store.unwrap_store())

        return self

    def add_db(self, db, store, description=None):
        self._importer_command.add_db(db, LocalStoreWrapper.from_store(db.db_id, store, crate=self), {} if description is None else description)
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
