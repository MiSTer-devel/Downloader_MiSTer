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

from collections import defaultdict
import os
from typing import Any, Dict, Iterable, List, Set, Tuple

from downloader.constants import MEDIA_USB0
from downloader.file_filter import BadFileFilterPartException, FileFilterFactory, FileFoldersHolder
from downloader.free_space_reservation import Partition, UnlimitedFreeSpaceReservation
from downloader.importer_command import ImporterCommand, ImporterCommandFactory
from downloader.interruptions import Interruptions
from downloader.job_system import JobFailPolicy, JobSystem
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl, InstallationReport
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorkerFailPolicy, make_downloader_worker_context
from downloader.local_store_wrapper import StoreFragmentDrivePaths
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter, WrongDatabaseOptions
from downloader.path_package import PathPackage, PathType, RemovedCopy
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.logger import NoLogger

from test.fake_http_gateway import FakeHttpGateway
from test.fake_job_system import ProgressReporterTracker
from test.fake_local_store_wrapper import StoreWrapper, LocalStoreWrapper
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
    def __init__(self, file_downloader_factory=None, config=None, file_system_factory=None, path_resolver_factory=None, local_repository=None, free_space_reservation=None, waiter=None, logger=None, path_dictionary=None, network_state=None, file_system_state=None):
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
            fail_policy=DownloaderWorkerFailPolicy.FAIL_FAST
        )

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

    def download_dbs_contents(self, importer_command: ImporterCommand, full_resync: bool):
        #return super().download_dbs_contents(importer_command, full_resync)
        
        for k, v in importer_command._config.items():
            self._config[k] = v

        for db, store, config in importer_command.read_dbs():
            self.add_db(db, store if isinstance(store, dict) else store.unwrap_store(), {})

        return self.download(full_resync)

    def download(self, full_resync):

        local_store = LocalStoreWrapper({'dbs': {db.db_id: store for db, store, _ in self.dbs}})

        self._job_system.register_workers({w.job_type_id(): w for w in make_workers(self._worker_ctx)})

        stores = {}
        jobs = []
        #db_test_filename = self.file_system.unique_temp_filename(register=False).value

        for db, store, ini_description in self.dbs:
            stores[db.db_id] = local_store.store_by_id(db.db_id)
            jobs.append(ProcessDbJob(db=db, ini_description=ini_description, store=stores[db.db_id], full_resync=full_resync))
            #db_temp_file_path = db_test_filename + '.db_temp_file_path.' + db.db_id + '.' + str(len(jobs)) + '.test_downloader'
            #self.file_system.save_json(db.testable, db_temp_file_path)
            #jobs.append(OpenDbJob(section=db.db_id, temp_path=db_temp_file_path, ini_description=ini_description, store=stores[db.db_id], full_resync=full_resync, get_file_job=None))

        for job in jobs: self._job_system.push_job(job)

        self._job_system.execute_jobs()

        report = self._worker_ctx.file_download_session_logger.report()
        box = InstallationBox()
        for job in report.get_completed_jobs(ProcessIndexJob):
            box.add_present_not_validated_files(job.present_not_validated_files)
            box.add_present_validated_files(job.present_validated_files)
            box.add_skipped_updated_files(job.skipped_updated_files)
            box.add_removed_copies(job.removed_copies)
            box.add_full_partitions(job.full_partitions)
            box.add_failed_files(job.failed_files_no_space)
            box.add_installed_folders(job.installed_folders)
            box.queue_directory_removal(job.directories_to_remove, job.db.db_id)
            box.queue_file_removal(job.files_to_remove, job.db.db_id)

        for job in report.get_completed_jobs(FetchFileJob2) + report.get_completed_jobs(CopyFileJob):
            if job.silent: continue
            box.add_downloaded_file(job.info)

        for job in report.get_completed_jobs(ValidateFileJob):
            box.add_downloaded_file(job.fetch_job.path)

        for job in report.get_completed_jobs(ValidateFileJob2):
            if job.after_job is not None: continue
            box.add_validated_file(job.info)

        for job in report.get_completed_jobs(ProcessZipJob):
            box.add_full_partitions(job.full_partitions)
            box.add_failed_files(job.failed_files_no_space)
            if job.has_new_zip_index:
                box.add_installed_zip_index(job.db.db_id, job.zip_id, job.result_zip_index, job.zip_description)

        for job in report.get_completed_jobs(OpenZipContentsJob):
            box.add_downloaded_files(job.downloaded_files)
            box.add_validated_files(job.downloaded_files)  # @TODO: Check the old implementation, didn't we check the hashes after unzipping?
            # We shoould be able to comment previous line and the test still pass
            box.add_failed_files(job.failed_files)
            box.add_filtered_zip_data(job.db.db_id, job.zip_id, job.filtered_data)
            box.add_installed_folders(job.installed_folders)
            box.queue_directory_removal(job.directories_to_remove, job.db.db_id)
            box.queue_file_removal(job.files_to_remove, job.db.db_id)

        for job, _e in report.get_failed_jobs(ValidateFileJob):
            box.add_failed_file(job.fetch_job.path)

        for job, _e in report.get_failed_jobs(ValidateFileJob2):
            box.add_failed_file(job.get_file_job.info)

        for job, _e in report.get_failed_jobs(FetchFileJob):
            box.add_failed_file(job.path)

        for job, _e in report.get_failed_jobs(FetchFileJob2) + report.get_failed_jobs(CopyFileJob):
            box.add_failed_file(job.info)

        for job, e in report.get_failed_jobs(ProcessIndexJob):
            if not isinstance(e, BadFileFilterPartException): continue
            box.add_failed_db_options(WrongDatabaseOptions(f"Wrong custom download filter on database {job.db.db_id}. Part '{str(e)}' is invalid."))

        removed_files = []
        processed_files = defaultdict(list)
        for pkg, dbs in box.consume_files():
            for db_id in dbs:
                stores[db_id].write_only().remove_file(pkg.rel_path)
                stores[db_id].write_only().remove_file_from_zips(pkg.rel_path)

            if report.is_file_processed(pkg.rel_path): continue

            for db_id in dbs:
                if not stores[db_id].read_only().has_externals:
                    continue

                for drive in stores[db_id].read_only().external_drives:
                    file_path = os.path.join(drive, pkg.rel_path)
                    if self._worker_ctx.file_system.is_file(file_path):
                        self._worker_ctx.file_system.unlink(file_path)

            self._worker_ctx.file_system.unlink(pkg.full_path)
            processed_files[list(dbs)[0]].append(pkg)
            removed_files.append(pkg)

        for db_id, pkgs in processed_files.items():
            self._worker_ctx.installation_report.add_processed_files(pkgs, db_id)

        box.add_removed_files(removed_files)

        for pkg, dbs in sorted(box.consume_directories(), key=lambda x: len(x[0].full_path), reverse=True):
            if box.is_folder_installed(pkg.rel_path):
                # If a folder got installed by any db...
                # assert len(dbs) >=1
                # The for-loop is for when two+ dbs used to have the same folder but one of them has removed it, it should be kept because
                # one db still uses it. But it should be removed from the store in the other dbs.
                for db_id in dbs:
                    stores[db_id].write_only().remove_folder(pkg.rel_path)
                    stores[db_id].write_only().remove_folder_from_zips(pkg.rel_path)
                continue

            if self._worker_ctx.file_system.folder_has_items(pkg.full_path):
                continue

            if not pkg.is_pext_external_subfolder:
                self._worker_ctx.file_system.remove_folder(pkg.full_path)

            for db_id in dbs:
                stores[db_id].write_only().remove_folder(pkg.rel_path)
                stores[db_id].write_only().remove_folder_from_zips(pkg.rel_path)

        external_parents_by_db: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        parents_by_db: Dict[str, Set[str]] = defaultdict(set)

        def add_parent(el_pkg: PathPackage, db_id: str) -> None:
            if el_pkg.pext_props is not None:
                if el_pkg.is_pext_standard:
                    parents_by_db[db_id].add(el_pkg.pext_props.parent)
                else:
                    external_parents_by_db[db_id][el_pkg.pext_props.parent].add(el_pkg.pext_props.drive)

        for file_path in box.installed_files():
            file = report.processed_file(file_path)
            if 'reboot' in file.pkg.description and file.pkg.description['reboot']:
                self._needs_reboot = True

            add_parent(file.pkg, file.db_id)
    
        for file_path in box.present_not_validated_files() + box.installed_files():
            file = report.processed_file(file_path)

            for is_external, other_drive in stores[file.db_id].read_only().list_other_drives_for_file(file.pkg.rel_path, file.pkg.drive()):
                other_file = os.path.join(other_drive, file.pkg.rel_path)
                if not self._worker_ctx.file_system.is_file(other_file):
                    if is_external:
                        stores[file.db_id].write_only().remove_external_file(file.pkg.rel_path)
                    else:
                        stores[file.db_id].write_only().remove_local_file(file.pkg.rel_path)
                        
            stores[file.db_id].write_only().add_file_pkg(file.pkg)

            if file.pkg.pext_props is not None:
                for other in file.pkg.pext_props.other_drives:
                    if self._worker_ctx.file_system.is_file(os.path.join(other, file.pkg.rel_path)):
                        stores[file.db_id].write_only().add_external_file(other, file.pkg.rel_path, file.pkg.description)

        for folder_path in sorted(box.installed_folders(), key=lambda x: len(x), reverse=True):
            for db_id, folder_pkg in report.processed_folder(folder_path).items():
                if folder_pkg.is_pext_parent:
                    continue

                stores[db_id].write_only().add_folder_pkg(folder_pkg)
                add_parent(folder_pkg, db_id)

        for folder_path in sorted(box.installed_folders(), key=lambda x: len(x), reverse=True):
            for db_id, folder_pkg in report.processed_folder(folder_path).items():
                if not folder_pkg.is_pext_parent:
                    continue

                if folder_pkg.pext_props.parent in parents_by_db[db_id]:
                    stores[db_id].write_only().add_folder(folder_pkg.rel_path, folder_pkg.description)
                if folder_pkg.pext_props.parent in external_parents_by_db[db_id]:
                    for drive in external_parents_by_db[db_id][folder_pkg.pext_props.parent]:
                        stores[db_id].write_only().add_external_folder(drive, folder_pkg.rel_path, folder_pkg.description)

        for file_path in box.removed_files():
            file = report.processed_file(file_path)
            stores[file.db_id].write_only().remove_file(file.pkg.rel_path)

        for is_external, el_path, drive, ty in box.removed_copies():
            if ty == PathType.FILE:
                file = report.processed_file(el_path)
                if is_external:
                    stores[file.db_id].write_only().remove_external_file(el_path)
                else:
                    stores[file.db_id].write_only().remove_local_file(el_path)

            elif ty == PathType.FOLDER:
                for db_id, folder_pkg in report.processed_folder(el_path).items():
                    if is_external:
                        stores[db_id].write_only().remove_external_folder(drive, el_path)
                    else:
                        stores[db_id].write_only().remove_local_folder(el_path)

        for file_path in box.failed_files():
            if not report.is_file_processed(file_path):
                continue
            file = report.processed_file(file_path)
            stores[file.db_id].write_only().remove_file(file.pkg.rel_path)

        for file_path in box.skipped_updated_files():
            file = report.processed_file(file_path)
            if file.db_id not in self._new_files_not_overwritten:
                self._new_files_not_overwritten[file.db_id] = []
            self._new_files_not_overwritten[file.db_id].append(file.pkg.rel_path)

        for db_id, zip_id, zip_index, zip_description in box.installed_zip_indexes():
            stores[db_id].write_only().add_zip_index(zip_id, zip_index, zip_description)

        filtered_zip_data = {}
        for db_id, zip_id, files, folders in box.filtered_zip_data():
            if db_id not in filtered_zip_data:
                filtered_zip_data[db_id] = {}

            if len(files) == 0 and len(folders) == 0:
                continue

            if zip_id not in filtered_zip_data[db_id]:
                filtered_zip_data[db_id][zip_id] = {'files': {}, 'folders': {}}

            filtered_zip_data[db_id][zip_id]['files'].update(files)
            filtered_zip_data[db_id][zip_id]['folders'].update(folders)

        for db_id, filtered_zip_data_by_db in filtered_zip_data.items():
            stores[db_id].write_only().save_filtered_zip_data(filtered_zip_data_by_db)

        for store in stores.values():
            store.write_only().cleanup_externals()

        self.needs_save = local_store.needs_save()

        for db, store, _ in self.dbs:
            self._clean_store(store)

        for e in box.wrong_db_options():
            raise e

        self._failed_files = box.failed_files()
        self._installed_files = box.installed_files()
        self._box = box
    
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
    
    def box(self) -> 'InstallationBox':
        return self._box

    @staticmethod
    def _clean_store(store):
        for file_description in store['files'].values():
            if 'tags' in file_description and 'zip_id' not in file_description: file_description.pop('tags')
        for folder_description in store['folders'].values():
            if 'tags' in folder_description and 'zip_id' not in folder_description: folder_description.pop('tags')
        for zip_description in store['zips'].values():
            if 'zipped_files' in zip_description['contents_file']:
                zip_description['contents_file'].pop('zipped_files')
            if 'summary_file' in zip_description and 'unzipped_json' in zip_description['summary_file']:
                zip_description['summary_file'].pop('unzipped_json')
            if 'internal_summary' in zip_description:
                zip_description.pop('internal_summary')


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


class InstallationBox:
    def __init__(self):
        self._downloaded_files: List[str] = []
        self._validated_files: List[str] = []
        self._present_validated_files: List[str] = []
        self._present_not_validated_files: List[str] = []
        self._fetch_started_files: List[str] = []
        self._failed_files: List[str] = []
        self._full_partitions: Dict[str, int] = dict()
        self._failed_db_options: List[WrongDatabaseOptions] = []
        self._removed_files: List[str] = []
        self._removed_copies: List[RemovedCopy] = []
        self._skipped_updated_files: List[str] = []
        self._filtered_zip_data: List[Tuple[str, str, Dict[str, Any], Dict[str, Any]]] = []
        self._installed_zip_indexes: List[Tuple[str, str, StoreFragmentDrivePaths, Dict[str, Any]]] = []
        self._installed_folders: Set[str] = set()
        self._directories = dict()
        self._files = dict()

    def add_downloaded_file(self, path: str):
        self._downloaded_files.append(path)
    def add_downloaded_files(self, files: List[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._downloaded_files.append(pkg.rel_path)
    def add_validated_file(self, path: str):
        self._validated_files.append(path)
    def add_validated_files(self, files: List[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._validated_files.append(pkg.rel_path)
    def add_installed_zip_index(self, db_id: str, zip_id: str, fragment: StoreFragmentDrivePaths, description: Dict[str, Any]):
        self._installed_zip_indexes.append((db_id, zip_id, fragment, description))
    def add_present_validated_files(self, paths: List[PathPackage]):
        if len(paths) == 0: return
        self._present_validated_files.extend([p.rel_path for p in paths])
    def add_present_not_validated_files(self, paths: List[PathPackage]):
        if len(paths) == 0: return
        self._present_not_validated_files.extend([p.rel_path for p in paths])
    def add_skipped_updated_files(self, paths: List[PathPackage]):
        if len(paths) == 0: return
        self._skipped_updated_files.extend([p.rel_path for p in paths])
    def add_file_fetch_started(self, path: str):
        self._fetch_started_files.append(path)
    def add_failed_file(self, path: str):
        self._failed_files.append(path)
    def add_failed_files(self, file_pkgs: List[PathPackage]):
        if len(file_pkgs) == 0: return
        for pkg in file_pkgs:
            self._failed_files.append(pkg.rel_path)
    def add_full_partitions(self, full_partitions: List[Tuple[Partition, int]]):
        if len(full_partitions) == 0: return
        for partition, failed_reserve in full_partitions:
            if partition.path not in self._full_partitions:
                self._full_partitions[partition.path] = failed_reserve
            else:
                self._full_partitions[partition.path] += failed_reserve

    def add_filtered_zip_data(self, db_id: str, zip_id: str, filtered_data: FileFoldersHolder) -> None:
        files, folders = filtered_data['files'], filtered_data['folders']
        #if len(files) == 0 and len(folders) == 0: return
        self._filtered_zip_data.append((db_id, zip_id, files, folders))

    def add_failed_db_options(self, exception: WrongDatabaseOptions):
        self._failed_db_options.append(exception)
    def add_removed_files(self, files: List[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._removed_files.append(pkg.rel_path)
    def add_removed_copies(self, copies: List[RemovedCopy]):
        if len(copies) == 0: return
        self._removed_copies.extend(copies)
    def add_installed_folders(self, folders: List[PathPackage]):
        if len(folders) == 0: return
        for pkg in folders:
            self._installed_folders.add(pkg.rel_path)

    def is_folder_installed(self, path: str) -> bool:  return path in self._installed_folders
    def downloaded_files(self): return self._downloaded_files
    def present_validated_files(self): return self._present_validated_files
    def present_not_validated_files(self): return self._present_not_validated_files
    def fetch_started_files(self): return self._fetch_started_files
    def failed_files(self): return self._failed_files
    def removed_files(self): return self._removed_files
    def removed_copies(self): return self._removed_copies
    def installed_files(self): return list(set(self._present_validated_files) | set(self._validated_files))
    def installed_folders(self): return list(self._installed_folders)
    def uninstalled_files(self): return self._removed_files + self._failed_files
    def wrong_db_options(self): return self._failed_db_options
    def installed_zip_indexes(self): return self._installed_zip_indexes
    def skipped_updated_files(self): return self._skipped_updated_files
    def filtered_zip_data(self): return self._filtered_zip_data
    def full_partitions_iter(self) -> Iterable[Tuple[str, int]]: return self._full_partitions.items()

    def queue_directory_removal(self, dirs: List[PathPackage], db_id: str) -> None:
        if len(dirs) == 0: return
        for pkg in dirs:
            self._directories.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)
    def queue_file_removal(self, files: List[PathPackage], db_id: str) -> None:
        if len(files) == 0: return
        for pkg in files:
            self._files.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)

    def consume_files(self) -> List[Tuple[PathPackage, Set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._files.values()], key=lambda x: x[0].rel_path)
        self._files.clear()
        return result

    def consume_directories(self) -> List[Tuple[PathPackage, Set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._directories.values()], key=lambda x: len(x[0].rel_path))
        self._directories.clear()
        return result
    