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

from typing import Any, Dict, List, Optional
from downloader.config import Config, ConfigDatabaseSection
from downloader.constants import MEDIA_USB0
from downloader.db_entity import DbEntity
from downloader.db_utils import DbSectionPackage
from downloader.file_filter import FileFilterFactory
from downloader.free_space_reservation import FreeSpaceReservation, UnlimitedFreeSpaceReservation
from downloader.interruptions import Interruptions
from downloader.job_system import Job, JobFailPolicy, JobSystem
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl, InstallationReport
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerFailPolicy, make_downloader_worker_context
from downloader.local_store_wrapper import StoreWrapper
from downloader.online_importer import InstallationBox, OnlineImporter as ProductionOnlineImporter
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.logger import Logger, NoLogger

from downloader.waiter import Waiter
from test.fake_http_gateway import FakeHttpGateway
from test.fake_job_system import ProgressReporterTracker
from test.fake_local_store_wrapper import LocalStoreWrapper
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_workers_factory import make_workers
from test.objects import config_with
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, FileSystemState, NetworkState
from test.fake_file_system_factory import FileSystemFactory


class OnlineImporter(ProductionOnlineImporter):
    def __init__(
        self,
        config: Optional[Config] = None,
        file_system_factory: Optional[FileSystemFactory] = None,
        free_space_reservation: Optional[FreeSpaceReservation] = None,
        waiter: Optional[Waiter] = None,
        logger: Optional[Logger] = None,
        file_filter_factory: Optional[FileFilterFactory] = None,
        path_dictionary: Optional[Dict[str, Any]] = None,
        network_state: Optional[NetworkState] = None,
        file_system_state: Optional[FileSystemState] = None,
        fail_policy: Optional[DownloaderWorkerFailPolicy] = None,
        start_on_db_processing: bool = True
    ):
        self._config = config or config_with(base_system_path=MEDIA_USB0)
        if isinstance(file_system_factory, FileSystemFactory):
            self.fs_factory = file_system_factory
            self.file_system_state = file_system_factory.private_state
        else:
            self.file_system_state = file_system_state or FileSystemState(config=self._config, path_dictionary=path_dictionary)
            self.fs_factory = file_system_factory or FileSystemFactory(state=self.file_system_state)

        self.file_system = self.fs_factory.create_for_system_scope()
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
            progress_reporter=self._report_tracker,
            file_download_session_logger=self._file_download_reporter,
            installation_report=installation_report,
            free_space_reservation=free_space_reservation or UnlimitedFreeSpaceReservation(),
            external_drives_repository=ExternalDrivesRepository(file_system=self.file_system),
            file_filter_factory=file_filter_factory or FileFilterFactory(NoLogger()),
            target_paths_calculator_factory=TargetPathsCalculatorFactory(self.file_system, external_drives_repository),
            config=self._config,
            fail_policy=fail_policy or DownloaderWorkerFailPolicy.FAIL_FAST
        )

        self._start_on_db_processing = start_on_db_processing

        super().__init__(
            logger,
            job_system=self._job_system,
            worker_ctx=self._worker_ctx,
            free_space_reservation=free_space_reservation or UnlimitedFreeSpaceReservation()
        )

        self.dbs = []

    def _make_workers(self) -> Dict[int, DownloaderWorker]:
        return {w.job_type_id(): w for w in make_workers(self._worker_ctx)}

    def _make_jobs(self, db_pkgs: List[DbSectionPackage], local_store: LocalStoreWrapper, full_resync: bool) -> List[Job]:
        if not self._start_on_db_processing:
            return super()._make_jobs(db_pkgs, local_store, full_resync)

        jobs = []
        for db, _store, ini_description in self.dbs:
            jobs.append(ProcessDbJob(db=db, ini_description=ini_description, store=local_store.store_by_id(db.db_id), full_resync=full_resync))
        return jobs

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs, free_space_reservation=None):
        config = implicit_inputs.config
        file_system_factory = FileSystemFactory(state=implicit_inputs.file_system_state, config=config)
        return OnlineImporter(
            config=config,
            file_system_factory=file_system_factory,
            free_space_reservation=free_space_reservation,
            network_state=implicit_inputs.network_state,
            file_system_state=implicit_inputs.file_system_state
        )

    @property
    def fs_data(self):
        return self.fs_factory.data

    @property
    def fs_records(self):
        return self.fs_factory.records

    @property
    def jobs_tracks(self):
        return self._report_tracker.tracks

    def download(self, full_resync: bool):
        self.set_local_store(LocalStoreWrapper({'dbs': {db.db_id: store for db, store, _ in self.dbs}}))
        db_pkgs: List[DbSectionPackage] = []
        for db, store, ini_description in self.dbs:
            db_pkgs.append(DbSectionPackage(db_id=db.db_id, section=ini_description, store=store))
        self.download_dbs_contents(db_pkgs, full_resync)
    
        return self

    def add_db(self, db: DbEntity, store: StoreWrapper=None, description: ConfigDatabaseSection=None):
        self.dbs.append((db, store or self._local_store.store_by_id(db.db_id), {} if description is None else description))
        return self

    def download_db(self, db, store, full_resync=False):
        self.add_db(db, store)
        self.download(full_resync)
        self._clean_store(store)
        return store

    def report(self) -> InstallationReport:
        return self._worker_ctx.file_download_session_logger.report()
    
    def box(self) -> InstallationBox:
        return self._box
