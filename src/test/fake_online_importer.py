# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import os
from collections import Counter
from enum import unique, Enum
from itertools import groupby
from operator import itemgetter
from typing import Any, Dict, List, Optional
from downloader.config import Config, ConfigDatabaseSection
from downloader.constants import MEDIA_USB0, DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE, \
    FILE_downloader_storage_json
from downloader.db_entity import DbEntity
from downloader.db_utils import DbSectionPackage
from downloader.file_filter import FileFilterFactory
from downloader.free_space_reservation import FreeSpaceReservation, UnlimitedFreeSpaceReservation
from downloader.interruptions import Interruptions
from downloader.job_system import JobFailPolicy, JobSystem, ProgressReporter
from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.load_local_store_job import LoadLocalStoreJob
from downloader.jobs.load_local_store_sigs_job import LoadLocalStoreSigsJob
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import FailCtx
from downloader.fail_policy import FailPolicy
from downloader.local_store_wrapper import StoreWrapper, empty_db_state_signature
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter, InstallationBox
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.logger import Logger
from downloader.waiter import Waiter
from downloader.job_system import WorkerResult, Job
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_data_worker import FetchDataWorker
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.worker_context import DownloaderWorker
from downloader.online_importer import OnlineImporterWorkersFactory as ProductionOnlineImporterWorkersFactory
from test.fake_file_system_factory import FakeFileSystem
from test.fake_store_migrator import StoreMigrator
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_http_gateway import FakeHttpGateway, FakeBuf
from test.fake_job_system import ProgressReporterTracker
from test.fake_local_store_wrapper import LocalStoreWrapper, local_store_wrapper
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_logger import NoLogger
from test.objects import config_with
from test.fake_waiter import NoWaiter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, FileSystemState, NetworkState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_local_repository import LocalRepository


@unique
class StartJobPolicy(Enum):
    OpeningDb = 0
    FetchDb = 1

class OnlineImporter(ProductionOnlineImporter):
    def __init__(
            self,
            config: Optional[Config] = None,
            file_system_factory: Optional[FileSystemFactory] = None,
            free_space_reservation: Optional[FreeSpaceReservation] = None,
            waiter: Optional[Waiter] = None,
            logger: Optional[Logger] = None,
            file_filter_factory: Optional[FileFilterFactory] = None,
            local_repository: Optional[LocalRepository] = None,
            base_path_relocator: Optional[BasePathRelocator] = None,
            job_system: Optional[JobSystem] = None,
            progress_reporter: Optional[ProgressReporter] = None,
            path_dictionary: Optional[Dict[str, Any]] = None,
            network_state: Optional[NetworkState] = None,
            file_system_state: Optional[FileSystemState] = None,
            fail_policy: Optional[FailPolicy] = None,
            job_fail_policy: Optional[JobFailPolicy] = None,
            start_job_policy: StartJobPolicy = StartJobPolicy.OpeningDb,
    ):
        self._config = config or config_with(base_system_path=MEDIA_USB0)
        if isinstance(file_system_factory, FileSystemFactory):
            self.fs_factory = file_system_factory
            self.file_system_state = file_system_factory.private_state
        else:
            self.file_system_state = file_system_state or FileSystemState(config=self._config,
                                                                          path_dictionary=path_dictionary)
            self.fs_factory = file_system_factory or FileSystemFactory(state=self.file_system_state)

        self.file_system = self.fs_factory.create_for_system_scope()
        self.network_state = network_state or NetworkState()
        waiter = NoWaiter() if waiter is None else waiter
        logger = NoLogger() if logger is None else logger
        http_gateway = FakeHttpGateway(self._config, self.network_state)
        self._file_download_reporter = FileDownloadProgressReporter(logger, waiter,
                                                                    Interruptions(fs=file_system_factory,
                                                                                  gw=http_gateway))
        self._report_tracker = progress_reporter or ProgressReporterTracker(self._file_download_reporter)
        self._job_system = job_system or JobSystem(self._report_tracker, logger=logger, max_threads=1,
                                                   fail_policy=job_fail_policy or JobFailPolicy.FAIL_FAST,
                                                   max_timeout=1)
        external_drives_repository = ExternalDrivesRepository(file_system=self.file_system)
        local_repository = local_repository or LocalRepository(config=self._config, file_system=self.file_system)
        base_path_relocator = base_path_relocator or BasePathRelocator(config=self._config,
                                                                       file_system_factory=self.fs_factory)
        old_pext_paths = set()
        file_filter_factory = file_filter_factory or FileFilterFactory(NoLogger())
        self._free_space_reservation = free_space_reservation or UnlimitedFreeSpaceReservation()
        online_importer_workers_factory = OnlineImporterWorkersFactory(
            worker_context=self._job_system,
            logger=logger,
            http_gateway=http_gateway,
            file_system=self.file_system,
            progress_reporter=self._report_tracker,
            local_repository=local_repository,
            base_path_relocator=base_path_relocator,
            file_download_reporter=self._file_download_reporter,
            free_space_reservation=self._free_space_reservation,
            file_filter_factory=file_filter_factory,
            target_paths_calculator_factory=TargetPathsCalculatorFactory(self.file_system, external_drives_repository, old_pext_paths),
            fail_ctx=FailCtx(logger, fail_policy=fail_policy or FailPolicy.FAIL_FAST),
            config=self._config
        )
        self._start_job_policy = start_job_policy
        self._local_store: Optional[LocalStoreWrapper] = None
        super().__init__(
            self._config,
            logger,
            file_system=self.file_system,
            file_filter_factory=file_filter_factory,
            file_download_reporter=self._file_download_reporter,
            fail_ctx=FailCtx(logger, fail_policy=fail_policy or FailPolicy.FAIL_FAST),
            job_system=self._job_system,
            worker_factory=online_importer_workers_factory,
            old_pext_paths=old_pext_paths
        )

        self.dbs = []
        self._store_file = os.path.join(self._config['base_system_path'], FILE_downloader_storage_json.lower())
        self._box: Optional[InstallationBox] = None
        self._error: Optional[Exception] = None

    def _make_jobs(self, db_pkgs: List[DbSectionPackage]) -> List[Job]:
        if self._start_job_policy == StartJobPolicy.FetchDb:
            return super()._make_jobs(db_pkgs)
        elif self._start_job_policy == StartJobPolicy.OpeningDb:  # @TODO: Consider removing this state and doing all from FetchDb with some tweaks in pre/post download methods.
            expanded_pkgs = {}
            new_db_pkgs = []
            for pkg in db_pkgs:
                expanded_pkgs[pkg.db_id] = {"section": pkg.section}
            for db, store, ini_description, store_sig, db_sig in self.dbs:
                expanded_pkgs[db.db_id]["db"] = db
                expanded_pkgs[db.db_id]["db_sig"] = db_sig or {}

            load_local_store_sigs_job = LoadLocalStoreSigsJob()
            load_local_store_sigs_job.local_store_sigs = empty_db_state_signature()
            load_local_store_job = LoadLocalStoreJob(new_db_pkgs, self._config)

            jobs = []
            for data in expanded_pkgs.values():
                db: DbEntity = data["db"]
                section: ConfigDatabaseSection = data["section"]
                new_db_pkgs.append(DbSectionPackage(db_id=db.db_id, section=section))

                db_sig = data["db_sig"]
                calcs = {
                    "hash": db_sig.get('hash', DB_STATE_SIGNATURE_NO_HASH),
                    "size": db_sig.get('size', DB_STATE_SIGNATURE_NO_SIZE)
                }
                transfer_job = CopyDataJob('db.json', {}, calcs, db.db_id)
                if isinstance(self.file_system, FakeFileSystem):
                    transfer_job.data = FakeBuf({"json": db.extract_props()})
                else:
                    import json, io
                    transfer_job.data = io.BytesIO(json.dumps(db.extract_props()).encode('utf-8'))
                jobs.append(OpenDbJob(
                    transfer_job=transfer_job,
                    section=db.db_id,
                    ini_description=section,
                    load_local_store_sigs_job=load_local_store_sigs_job,
                    load_local_store_job=load_local_store_job,
                ))

            return jobs

        raise Exception("Should not happen!")

    def download_dbs_contents(self, db_pkgs: list[DbSectionPackage]) -> tuple[InstallationBox, Optional[BaseException]]:
        if self._local_store is not None:
            self.file_system_state.files[self._store_file] = {
                "json": {
                    **self._local_store.unwrap_local_store(),
                    "migration_version": StoreMigrator().latest_migration_version()
                }
            }
        result = super().download_dbs_contents(db_pkgs)
        if self._store_file in self.file_system_state.files:
            self.file_system_state.files.pop(self._store_file)
        return result

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs, free_space_reservation=None,
                             fail_policy=FailPolicy.FAULT_TOLERANT_ON_CUSTOM_DOWNLOADER_ERRORS, logger=None):
        config = implicit_inputs.config
        file_system_factory = FileSystemFactory(state=implicit_inputs.file_system_state, config=config)
        return OnlineImporter(
            config=config,
            file_system_factory=file_system_factory,
            free_space_reservation=free_space_reservation,
            network_state=implicit_inputs.network_state,
            file_system_state=implicit_inputs.file_system_state,
            fail_policy=fail_policy,
            logger=logger
        )

    @property
    def fs_data(self):
        return self.fs_factory.data

    @property
    def fs_records(self):
        return self.fs_factory.records

    def jobs_tracks(self):
        sorted_jobs = sorted(
            [(k, tup[0]) for k, v in self._report_tracker.tracks.items() if isinstance(v, list) for tup in v],
            key=itemgetter(0))
        return {
            event_type: dict(Counter(job_name for _, job_name in group))
            for event_type, group in groupby(sorted_jobs, key=itemgetter(0))
        }

    @property
    def job_system(self):
        return self._job_system

    def box(self) -> Optional[InstallationBox]:
        return self._box

    def error(self) -> Optional[Exception]:
        return self._error

    def download(self):
        db_pkgs: List[DbSectionPackage] = []
        for db, store, ini_description, store_sig, db_sig in self.dbs:
            self._add_store(db.db_id, store, store_sig=store_sig)
            db_pkgs.append(DbSectionPackage(db_id=db.db_id, section=ini_description))
        self._box, self._error = self.download_dbs_contents(db_pkgs)
        return self

    def add_db(self, db: DbEntity, store: StoreWrapper = None, description: ConfigDatabaseSection = None,
               store_sig=None, db_sig=None):
        self.dbs.append((db, store, {} if description is None else description, store_sig, db_sig))
        return self

    def download_db(self, db, store):
        self.add_db(db, store)
        self.download()
        self._clean_store(store)
        return store

    def _add_store(self, db_id: str, store=None, store_sig=None):
        if self._local_store is None:
            self._local_store = local_store_wrapper({})

        if store is not None:
            self._local_store.unwrap_local_store()['dbs'][db_id] = store

        if store_sig is not None:
            self._local_store.unwrap_local_store()['db_sigs'][db_id] = store_sig

    def free_space(self):
        actual_remaining_space = dict(self._free_space_reservation.free_space())
        for p, reservation in self.box().full_partitions().items():
            actual_remaining_space[p] -= reservation
        return actual_remaining_space

class OnlineImporterWorkersFactory(ProductionOnlineImporterWorkersFactory):
    def create_workers(self):
        replacement_workers = []
        if isinstance(self._http_gateway, FakeHttpGateway):
            fake_http: FakeHttpGateway = self._http_gateway
            replacement_workers.extend([
                FakeWorkerDecorator(FetchFileWorker(
                    progress_reporter=self._progress_reporter, http_gateway=fake_http, file_system=self._file_system,
                    timeout=self._config['downloader_timeout'],
                ), fake_http),
                FakeWorkerDecorator(FetchDataWorker(
                    http_gateway=fake_http,
                    file_system=self._file_system,
                    progress_reporter=self._progress_reporter,
                    fail_ctx=self._fail_ctx,
                    timeout=self._config['downloader_timeout'],
                ), fake_http),
            ])

        replacement_type_ids = {r.job_type_id() for r in replacement_workers}
        workers = [w for w in super().create_workers() if w.job_type_id() not in replacement_type_ids]
        return [*workers, *replacement_workers]


class FakeWorkerDecorator(DownloaderWorker):
    def __init__(self, worker: DownloaderWorker, fake_http: FakeHttpGateway):
        self._worker = worker
        self._fake_http = fake_http

    def job_type_id(self) -> int: return self._worker.job_type_id()
    def operate_on(self, job: Job) -> WorkerResult:
        if isinstance(job, FetchFileJob):
            self._fake_http.set_file_ctx({
                'description': {**job.pkg.description},
                'path': job.pkg.full_path,
                'info': job.pkg.rel_path
            })
        elif isinstance(job, FetchDataJob):
            self._fake_http.set_file_ctx({
                'description': {**job.description},
                'path': None,
                'info': None
            })
        try:
            return self._worker.operate_on(job)
        finally:
            self._fake_http.set_file_ctx(None)
