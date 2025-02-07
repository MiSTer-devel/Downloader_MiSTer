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
from downloader.interruptions import Interruptions
from downloader.job_system import JobFailPolicy, JobSystem
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl, InstallationReport
from downloader.jobs.worker_context import DownloaderWorkerFailPolicy, make_downloader_worker_context
from downloader.online_importer import InstallationBox, OnlineImporter as ProductionOnlineImporter
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.logger import NoLogger

from test.fake_http_gateway import FakeHttpGateway
from test.fake_job_system import ProgressReporterTracker
from test.fake_local_store_wrapper import LocalStoreWrapper
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_local_repository import LocalRepository
from test.fake_path_resolver import PathResolverFactory
from test.fake_workers_factory import make_workers
from test.objects import config_with
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, FileSystemState, NetworkState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_file_downloader_factory import FileDownloaderFactory


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, path_resolver_factory=None, local_repository=None, free_space_reservation=None, waiter=None, logger=None, path_dictionary=None, network_state=None, file_system_state=None, fail_policy=None):
        self._config = config or config_with(base_system_path=MEDIA_USB0)
        if isinstance(file_system_factory, FileSystemFactory):
            self.fs_factory = file_system_factory
            self.file_system_state = file_system_factory.private_state
        else:
            self.file_system_state = file_system_state or FileSystemState(config=self._config, path_dictionary=path_dictionary)
            self.fs_factory = file_system_factory or FileSystemFactory(state=self.file_system_state)

        file_downloader_factory = file_downloader_factory or FileDownloaderFactory(config=self._config, file_system_factory=self.fs_factory, state=self.file_system_state)
        self.file_system = self.fs_factory.create_for_system_scope()
        path_resolver_factory = path_resolver_factory or PathResolverFactory(path_dictionary=self.file_system_state.path_dictionary, file_system_factory=self.fs_factory)
        self.needs_save = False
        self._needs_reboot = False
        self._new_files_not_overwritten = {}
        waiter = NoWaiter() if waiter is None else waiter
        logger = NoLogger() if logger is None else logger
        installation_report = InstallationReportImpl()
        http_gateway = FakeHttpGateway(self._config, network_state or NetworkState())
        self._file_download_reporter = FileDownloadProgressReporter(logger, waiter, Interruptions(fs=file_system_factory, gw=http_gateway), installation_report)
        self._report_tracker = ProgressReporterTracker(self._file_download_reporter)
        self._job_system = JobSystem(self._report_tracker, logger=logger, max_threads=1, fail_policy=JobFailPolicy.FAIL_FAST, max_timeout=1)
        external_drives_repository = ExternalDrivesRepository(file_system=self.file_system)
        self._worker_ctx = make_downloader_worker_context(
            job_ctx=self._job_system,
            waiter=waiter,
            logger=logger,
            http_gateway=http_gateway,
            file_system=self.file_system,
            target_path_repository=None,
            progress_reporter=self._report_tracker,
            file_download_session_logger=self._file_download_reporter,
            installation_report=installation_report,
            free_space_reservation=free_space_reservation or UnlimitedFreeSpaceReservation(),
            external_drives_repository=ExternalDrivesRepository(file_system=self.file_system),
            target_paths_calculator_factory=TargetPathsCalculatorFactory(self.file_system, external_drives_repository),
            config=self._config,
            fail_policy=fail_policy or DownloaderWorkerFailPolicy.FAIL_FAST
        )

        super().__init__(
            FileFilterFactory(logger),
            self.fs_factory,
            file_downloader_factory,
            path_resolver_factory,
            LocalRepository(config=self._config, file_system=self.file_system, file_system_factory=self.fs_factory) if local_repository is None else local_repository,
            ExternalDrivesRepository(file_system=self.file_system),
            free_space_reservation or UnlimitedFreeSpaceReservation(),
            waiter,
            logger,
            job_system=self._job_system,
            worker_ctx=self._worker_ctx
            )

        self.dbs = []

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
            network_state=implicit_inputs.network_state,
            file_system_state=implicit_inputs.file_system_state
        )

    @property
    def fs_data(self):
        return self._file_system_factory.data

    @property
    def fs_records(self):
        return self._file_system_factory.records

    @property
    def jobs_tracks(self):
        return self._report_tracker.tracks
    
    def _make_workers(self, ctx):
        return {w.job_type_id(): w for w in make_workers(ctx)}
    
    def _make_jobs(self, importer_command, local_store, full_resync):
        jobs = []
        for db, store, ini_description in self.dbs:
            jobs.append(ProcessDbJob(db=db, ini_description=ini_description, store=local_store.store_by_id(db.db_id), full_resync=full_resync))
        return jobs

    def download(self, full_resync):
        self.set_local_store(LocalStoreWrapper({'dbs': {db.db_id: store for db, store, _ in self.dbs}}))

        importer_command = ImporterCommand('')
        for db, store, ini_description in self.dbs:
            importer_command.add_db(db.db_id, ini_description)
        self.download_dbs_contents(importer_command, full_resync)
    
        return self

    def new_files_not_overwritten(self):
        return self._new_files_not_overwritten

    def needs_reboot(self):
        return self._needs_reboot

    def full_partitions(self):
        return [p for p, s in self._box.full_partitions_iter()]

    def free_space(self):
        actual_remaining_space = dict(self._free_space_reservation.free_space())
        for p, reservation in self._box.full_partitions_iter():
            actual_remaining_space[p] -= reservation
        return actual_remaining_space

    def add_db(self, db, store, description=None):
        self.dbs.append((db, store, {} if description is None else description))
        return self

    def download_db(self, db, store, full_resync=False):
        self.add_db(db, store)
        self.download(full_resync)
        self._clean_store(store)
        return store

    def correctly_installed_files(self):
        return self._installed_files

    def files_that_failed(self):
        return self._failed_files

    def report(self) -> InstallationReport:
        return self._worker_ctx.file_download_session_logger.report()
    
    def box(self) -> InstallationBox:
        return self._box


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
