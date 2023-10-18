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
from downloader.free_space_reservation import UnlimitedFreeSpaceReservation
from downloader.importer_command import ImporterCommand, ImporterCommandFactory
from downloader.job_system import JobSystem
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorkerContext
from downloader.jobs.workers_factory import DownloaderWorkersFactory
from downloader.jobs.download_db_job import DownloadDbJob
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter
from test.fake_http_gateway import FakeHttpGateway
from test.fake_local_store_wrapper import StoreWrapper, LocalStoreWrapper
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_local_repository import LocalRepository
from test.fake_path_resolver import PathResolverFactory
from test.objects import config_with
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, FileSystemState, NetworkState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory
from downloader.logger import NoLogger


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, path_resolver_factory=None, local_repository=None, free_space_reservation=None, waiter=None, logger=None, path_dictionary=None, network_state=None):
        self._config = config if config is not None else config_with(base_system_path=MEDIA_USB0)
        file_system_state = FileSystemState(config=self._config, path_dictionary=path_dictionary)
        self.fs_factory = FileSystemFactory(state=file_system_state) if file_system_factory is None else file_system_factory
        file_downloader_factory = FileDownloaderFactory(config=config, file_system_factory=self.fs_factory, state=file_system_state) if file_downloader_factory is None else file_downloader_factory
        self.file_system = self.fs_factory.create_for_system_scope()
        path_resolver_factory = PathResolverFactory(path_dictionary=file_system_state.path_dictionary, file_system_factory=self.fs_factory) if path_resolver_factory is None else path_resolver_factory

        self.needs_save = False
        self._needs_reboot = False
        self._new_files_not_overwritten = {}
        waiter = NoWaiter() if waiter is None else waiter
        logger = NoLogger() if logger is None else logger

        super().__init__(
            FileFilterFactory(logger),
            self.fs_factory,
            file_downloader_factory,
            path_resolver_factory,
            LocalRepository(config=self._config, file_system=self.file_system, file_system_factory=self.fs_factory) if local_repository is None else local_repository,
            ExternalDrivesRepository(file_system=self.file_system),
            free_space_reservation or UnlimitedFreeSpaceReservation(),
            waiter,
            logger)

        self.dbs = []
        installation_report = InstallationReportImpl()
        self._file_download_reporter = FileDownloadProgressReporter(logger, waiter, installation_report)
        self._job_system = JobSystem(self._file_download_reporter, logger=logger, max_threads=1)
        self._worker_ctx = DownloaderWorkerContext(
            job_system=self._job_system,
            waiter=waiter,
            logger=logger,
            http_gateway=FakeHttpGateway(self._config, network_state or NetworkState()),
            file_system=self.file_system,
            target_path_repository=None,
            file_download_reporter=self._file_download_reporter,
            installation_report=installation_report,
            free_space_reservation=UnlimitedFreeSpaceReservation(),
            external_drives_repository=ExternalDrivesRepository(file_system=self.file_system),
            config=self._config
        )
        self._workers_factory = DownloaderWorkersFactory(self._worker_ctx)

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs, free_space_reservation=None):
        file_downloader_factory, file_system_factory, config = FileDownloaderFactory.from_implicit_inputs(implicit_inputs)

        path_resolver_factory = PathResolverFactory.from_file_system_state(implicit_inputs.file_system_state)

        return OnlineImporter(
            config=config,
            file_system_factory=file_system_factory,
            file_downloader_factory=file_downloader_factory,
            path_resolver_factory=path_resolver_factory,
            free_space_reservation=free_space_reservation,
            network_state=implicit_inputs.network_state
        )

    @property
    def fs_data(self):
        return self._file_system_factory.data

    @property
    def fs_records(self):
        return self._file_system_factory.records

    def download(self, full_resync):

        local_store = LocalStoreWrapper({'dbs': {db.db_id: store for db, store, _ in self.dbs}})

        self._workers_factory.prepare_workers()

        stores = {}
        for db, store, ini_description in self.dbs:
            stores[db.db_id] = local_store.store_by_id(db.db_id)
            self._job_system.push_job(ProcessDbJob(db=db, ini_description=ini_description, store=stores[db.db_id], full_resync=full_resync))

        self._job_system.accomplish_pending_jobs()

        report = self._worker_ctx.file_download_reporter.report()
        for file_path in report.installed_files():
            file = report.processed_file(file_path)
            if 'reboot' in file.desc and file.desc['reboot']:
                self._needs_reboot = True
            stores[file.db_id].write_only().add_file(file.path, file.desc)

        for file_path in report.uninstalled_files():
            file = report.processed_file(file_path)
            stores[file.db_id].write_only().remove_file(file.path)

        for file_path in report.skipped_updated_files():
            file = report.processed_file(file_path)
            if file.db_id not in self._new_files_not_overwritten:
                self._new_files_not_overwritten[file.db_id] = []
            self._new_files_not_overwritten[file.db_id].append(file.path)

        for db, store, _ in self.dbs:
            self._clean_store(store)

        self.needs_save = local_store.needs_save()

        return self

    def new_files_not_overwritten(self):
        return self._new_files_not_overwritten

    def needs_reboot(self):
        return self._needs_reboot

    def add_db(self, db, store, description=None):
        self.dbs.append((db, store, {} if description is None else description))
        return self

    def download_db(self, db, store, full_resync=False):
        self.add_db(db, store)
        self.download(full_resync)
        self._clean_store(store)
        return store

    def correctly_installed_files(self):
        return self._worker_ctx.file_download_reporter.report().installed_files()

    def files_that_failed(self):
        return self._worker_ctx.file_download_reporter.report().failed_files()

    @staticmethod
    def _clean_store(store):
        for zip_description in store['zips'].values():
            if 'zipped_files' in zip_description['contents_file']:
                zip_description['contents_file'].pop('zipped_files')
            if 'summary_file' in zip_description and 'unzipped_json' in zip_description['summary_file']:
                zip_description['summary_file'].pop('unzipped_json')


class OnlineImporter2(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, path_resolver_factory=None, local_repository=None, free_space_reservation=None, waiter=None, logger=None, path_dictionary=None):
        self._config = config if config is not None else config_with(base_system_path=MEDIA_USB0)
        file_system_state = FileSystemState(config=self._config, path_dictionary=path_dictionary)
        self.fs_factory = FileSystemFactory(state=file_system_state) if file_system_factory is None else file_system_factory
        file_downloader_factory = FileDownloaderFactory(config=config, file_system_factory=self.fs_factory) if file_downloader_factory is None else file_downloader_factory
        self.file_system = self.fs_factory.create_for_system_scope()
        path_resolver_factory = PathResolverFactory(path_dictionary=file_system_state.path_dictionary) if path_resolver_factory is None else path_resolver_factory

        self.needs_save = False

        super().__init__(
            FileFilterFactory(NoLogger() if logger is None else logger),
            self.fs_factory,
            file_downloader_factory,
            path_resolver_factory,
            LocalRepository(config=self._config, file_system=self.file_system) if local_repository is None else local_repository,
            ExternalDrivesRepository(file_system=self.file_system),
            free_space_reservation or UnlimitedFreeSpaceReservation(),
            NoWaiter() if waiter is None else waiter,
            NoLogger() if logger is None else logger)

        self._importer_command = ImporterCommand(self._config, [])

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs, free_space_reservation=None):
        file_downloader_factory, file_system_factory, config = FileDownloaderFactory.from_implicit_inputs(implicit_inputs)

        path_resolver_factory = PathResolverFactory.from_file_system_state(implicit_inputs.file_system_state)

        return OnlineImporter(config=config, file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory, path_resolver_factory=path_resolver_factory, free_space_reservation=free_space_reservation)

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
        self._importer_command.add_db(db, StoreWrapper(store, crate=self), {} if description is None else description)
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


class ImporterCommandFactorySpy(ImporterCommandFactory):
    def __init__(self, config):
        super().__init__(config)
        self._commands = []

    def create(self):
        command = super().create()
        self._commands.append(command)
        return command

    def commands(self):
        return [[(x.testable, y.unwrap_store(), z) for x, y, z in c.read_dbs()] for c in self._commands]
