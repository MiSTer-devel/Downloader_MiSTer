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

import sys
from typing import Optional, Any
from collections import defaultdict
import os

from downloader.config import Config
from downloader.constants import FILE_MiSTer, EXIT_ERROR_BAD_NEW_BINARY, MEDIA_FAT
from downloader.db_entity import DbEntity
from downloader.db_utils import DbSectionPackage
from downloader.error import DownloaderError
from downloader.job_system import Job, Worker
from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.errors import WrongDatabaseOptions, FileDownloadError
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.jobs_factory import make_transfer_job
from downloader.jobs.load_local_store_job import LoadLocalStoreJob, local_store_tag
from downloader.jobs.load_local_store_sigs_job import LoadLocalStoreSigsJob, local_store_sigs_tag
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.reporters import InstallationReport
from downloader.jobs.worker_context import DownloaderWorkerContext
from downloader.jobs.workers_factory import make_workers
from downloader.logger import Logger
from downloader.file_filter import BadFileFilterPartException, FileFoldersHolder
from downloader.free_space_reservation import FreeSpaceReservation, Partition
from downloader.job_system import JobSystem
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.local_store_wrapper import LocalStoreWrapper, StoreFragmentDrivePaths
from downloader.path_package import PathPackage


class OnlineImporter:
    def __init__(self, logger: Logger, job_system: JobSystem, worker_ctx: DownloaderWorkerContext, free_space_reservation: FreeSpaceReservation, old_pext_paths: set[str]) -> None:
        self._logger = logger
        self._job_system = job_system
        self._worker_ctx = worker_ctx
        self._free_space_reservation = free_space_reservation
        self._old_pext_paths = old_pext_paths
        self._box = InstallationBox()
        self._local_store: Optional[LocalStoreWrapper] = None
        self._first_time = True

    def _make_workers(self) -> dict[int, Worker]:
        return {w.job_type_id(): w for w in make_workers(self._worker_ctx)}

    def _make_jobs(self, db_pkgs: list[DbSectionPackage]) -> list[Job]:
        jobs: list[Job] = []
        load_local_store_sigs_job = LoadLocalStoreSigsJob()
        load_local_store_sigs_job.add_tag(local_store_sigs_tag)
        load_local_store_job = LoadLocalStoreJob(db_pkgs, self._worker_ctx.config)
        load_local_store_job.add_tag(local_store_tag)
        for pkg in db_pkgs:
            transfer_job = make_transfer_job(pkg.section['db_url'], {}, True, pkg.db_id)
            transfer_job.after_job = OpenDbJob(  # type: ignore[union-attr]
                transfer_job=transfer_job,
                section=pkg.db_id,
                ini_description=pkg.section,
                load_local_store_sigs_job=load_local_store_sigs_job,
                load_local_store_job=load_local_store_job,
            )
            jobs.append(transfer_job)  # type: ignore[arg-type]
        jobs.insert(int(len(jobs) / 2) + 1, load_local_store_sigs_job)
        return jobs

    def download_dbs_contents(self, db_pkgs: list[DbSectionPackage]) -> Optional[BaseException]:
        logger = self._logger
        logger.bench('OnlineImporter start.')

        self._job_system.register_workers(self._make_workers())
        self._job_system.push_jobs(self._make_jobs(db_pkgs))

        file_mister_present = self._worker_ctx.file_system.is_file(os.path.join(MEDIA_FAT, FILE_MiSTer), use_cache=False)

        logger.bench('OnlineImporter execute jobs start.')
        self._job_system.pending_jobs_amount()
        self._job_system.execute_jobs()
        self._worker_ctx.file_download_session_logger.print_pending()
        logger.bench('OnlineImporter execute jobs done.')

        if self._first_time:
            self._first_time = False
        else:
            # @TODO: Maybe use a factory to avoid resetting state
            self._box = InstallationBox()
            self._worker_ctx.installation_report.reset()

        box = self._box
        report: InstallationReport = self._worker_ctx.installation_report

        box.set_unused_filter_tags(self._worker_ctx.file_filter_factory.unused_filter_parts())
        box.set_old_pext_paths(self._old_pext_paths)

        for fetch_file_job in report.get_started_jobs(FetchFileJob):
            box.add_file_fetch_started(fetch_file_job.pkg.rel_path)

        for fetch_file_job in report.get_completed_jobs(FetchFileJob):
            if fetch_file_job.db_id is None or fetch_file_job.pkg is None: continue
            box.add_downloaded_file(fetch_file_job.pkg.rel_path)
            box.add_validated_file(fetch_file_job.pkg, fetch_file_job.db_id)

        for fetch_file_job, e in report.get_failed_jobs(FetchFileJob):
            box.add_failed_file(fetch_file_job.pkg.rel_path)
            if fetch_file_job.pkg.rel_path != FILE_MiSTer or not file_mister_present:
                continue

            self._logger.debug(e)
            fs = self._worker_ctx.file_system
            full_path = fetch_file_job.pkg.full_path
            if fs.is_file(full_path, use_cache=False):
                continue

            backup_path = fetch_file_job.pkg.backup_path()
            temp_path = fetch_file_job.pkg.temp_path(fetch_file_job.already_exists)
            if backup_path is not None and fs.is_file(backup_path, use_cache=False):
                fs.move(backup_path, full_path)
            elif temp_path is not None and fs.is_file(temp_path, use_cache=False) and fs.hash(temp_path) == fetch_file_job.pkg.description['hash']:
                fs.move(temp_path, full_path)

            if fs.is_file(full_path, use_cache=False):
                continue

            # This error message should never happen.
            # If it happens it would be an unexpected case where file_system is not moving files correctly
            self._logger.print('CRITICAL ERROR!!! Could not restore the MiSTer binary!')
            self._logger.print('Please manually rename the file MiSTer.new as MiSTer')
            self._logger.print('Your system won\'nt be able to boot until you do so!')
            sys.exit(EXIT_ERROR_BAD_NEW_BINARY)

        db_fetch_success = 0
        for fetch_data_job in report.get_completed_jobs(FetchDataJob):
            if isinstance(fetch_data_job.after_job, OpenDbJob):
                db_fetch_success += 1

        db_fetch_errors = 0
        for transfer_job, e in report.get_failed_jobs(FetchDataJob) + report.get_failed_jobs(CopyDataJob):
            if isinstance(transfer_job, FetchDataJob) and isinstance(e, FileDownloadError) and isinstance(transfer_job.after_job, OpenDbJob):
                db_fetch_errors += 1

            box.add_failed_file(transfer_job.source)  # @TODO: This should not count as a file, but as a "source".
            if transfer_job.db_id is None:
                continue

            if any(':zip:' in tag for tag in transfer_job.tags):
                continue

            box.add_failed_db(transfer_job.db_id)

        logger.bench('OnlineImporter determining network problems...')

        network_problems = db_fetch_success == 0 and db_fetch_errors > 0
        if network_problems:
            logger.bench('OnlineImporter could not progress with network problems.')
            return NetworkProblems(f'Network problems detected. db_fetch_success == {db_fetch_success} and db_fetch_errors == {db_fetch_errors}')

        for open_db_job in report.get_completed_jobs(OpenDbJob):
            if open_db_job.skipped is True:
                box.add_skipped_db(open_db_job.section)

        for open_db_job, _e in report.get_failed_jobs(OpenDbJob):
            box.add_failed_db(open_db_job.section)

        for mount_store_db_job in report.get_completed_jobs(MixStoreAndDbJob):
            if mount_store_db_job.skipped is True:
                box.add_skipped_db(mount_store_db_job.db.db_id)

        for mount_store_db_job, _e in report.get_failed_jobs(MixStoreAndDbJob):
            box.add_failed_db(mount_store_db_job.db.db_id)

        if len(box.skipped_dbs()) == len(db_pkgs):
            logger.bench('OnlineImporter early end.')
            logger.debug('Skipping all dbs!')
            return None

        logger.bench('OnlineImporter applying changes on stores...')

        # There is a totally legit case of not loading the store, and that not being an error
        # That happens when all DBs are skipped due to non strict file checking
        # Also, when the dbs error (for example for db_props failed validation), we don't ever launch
        # the load store job, so that's also normal. And in that case, the error is failed db, and
        # not failed store load.

        local_store_err: Optional[BaseException] = None
        load_local_store_jobs = report.get_completed_jobs(LoadLocalStoreJob)
        if len(load_local_store_jobs) >= 1:
            self._local_store = load_local_store_jobs[0].local_store
        elif self._local_store is None:
            load_local_store_job_errors = report.get_failed_jobs(LoadLocalStoreJob)
            if len(load_local_store_job_errors) > 0:
                local_store_err = load_local_store_job_errors[0][1]
            elif len(report.get_started_jobs(LoadLocalStoreJob)) > 0:
                local_store_err = DownloaderError('Local Store was not loaded.')

        for db_job in report.get_completed_jobs(ProcessDbMainJob):
            box.add_installed_db(db_job.db, db_job.config, db_job.db_hash, db_job.db_size)
            for zip_id in db_job.ignored_zips:
                box.add_failed_zip(db_job.db.db_id, zip_id)
            for zip_id in db_job.removed_zips:
                box.add_removed_zip(db_job.db.db_id, zip_id)

        for db_job, _e in report.get_failed_jobs(ProcessDbMainJob):
            box.add_failed_db(db_job.db.db_id)

        for index_job in report.get_completed_jobs(ProcessDbIndexJob):
            box.add_present_not_validated_files(index_job.present_not_validated_files)
            box.add_verified_integrity_files(index_job.verified_integrity_pkgs, index_job.db.db_id)
            box.add_duplicated_files(index_job.duplicated_files, index_job.db.db_id)
            box.add_non_duplicated_files(index_job.non_duplicated_files, index_job.db.db_id)
            box.add_present_validated_files(index_job.present_validated_files, index_job.db.db_id)
            box.add_skipped_updated_files(index_job.skipped_updated_files, index_job.db.db_id)
            box.add_repeated_store_presence(index_job.repeated_store_presence, index_job.db.db_id)
            box.add_removed_folders(index_job.removed_folders, index_job.db.db_id)
            box.add_installed_folders(index_job.installed_folders, index_job.db.db_id)
            box.queue_directory_removal(index_job.directories_to_remove, index_job.db.db_id)
            box.queue_file_removal(index_job.files_to_remove, index_job.db.db_id)

        for index_job, e in report.get_failed_jobs(ProcessDbIndexJob):
            box.add_failed_db(index_job.db.db_id)
            box.add_full_partitions(index_job.full_partitions)
            box.add_failed_files(index_job.failed_files_no_space)
            box.add_failed_folders(index_job.failed_folders)
            if not isinstance(e, BadFileFilterPartException): continue
            box.add_failed_db_options(WrongDatabaseOptions(f"Wrong custom download filter on database {index_job.db.db_id}. Part '{str(e)}' is invalid."))

        for zindex_job in report.get_completed_jobs(ProcessZipIndexJob):
            box.add_present_not_validated_files(zindex_job.present_not_validated_files)
            box.add_verified_integrity_files(zindex_job.verified_integrity_pkgs, zindex_job.db.db_id)
            box.add_duplicated_files(zindex_job.duplicated_files, zindex_job.db.db_id)
            box.add_non_duplicated_files(zindex_job.non_duplicated_files, zindex_job.db.db_id)
            box.add_present_validated_files(zindex_job.present_validated_files, zindex_job.db.db_id)
            box.add_skipped_updated_files(zindex_job.skipped_updated_files, zindex_job.db.db_id)
            box.add_repeated_store_presence(zindex_job.repeated_store_presence, zindex_job.db.db_id)
            box.add_removed_folders(zindex_job.removed_folders, zindex_job.db.db_id)
            box.add_installed_folders(zindex_job.installed_folders, zindex_job.db.db_id)
            box.queue_directory_removal(zindex_job.directories_to_remove, zindex_job.db.db_id)
            box.queue_file_removal(zindex_job.files_to_remove, zindex_job.db.db_id)
            if zindex_job.summary_download_failed is not None:
                box.add_failed_file(zindex_job.summary_download_failed)
            if zindex_job.filtered_data:
                box.add_filtered_zip_data(zindex_job.db.db_id, zindex_job.zip_id, zindex_job.filtered_data)
            if zindex_job.has_new_zip_summary:
                box.add_installed_zip_summary(zindex_job.db.db_id, zindex_job.zip_id, zindex_job.result_zip_index, zindex_job.zip_description)

        for zindex_job, _e in report.get_failed_jobs(ProcessZipIndexJob):
            box.add_failed_zip(zindex_job.db.db_id, zindex_job.zip_id)
            if zindex_job.summary_download_failed is not None:
                box.add_failed_file(zindex_job.summary_download_failed)
            box.add_failed_files(zindex_job.failed_files_no_space)
            box.add_full_partitions(zindex_job.full_partitions)
            box.add_failed_folders(zindex_job.failed_folders)

        for open_zip_job in report.get_completed_jobs(OpenZipContentsJob):
            box.add_downloaded_files(open_zip_job.downloaded_files)
            box.add_validated_files(open_zip_job.validated_files, open_zip_job.db.db_id)
            # We should be able to comment previous line and the test still pass
            box.add_failed_files(open_zip_job.failed_files)
            box.queue_directory_removal(open_zip_job.directories_to_remove, open_zip_job.db.db_id)
            box.queue_file_removal(open_zip_job.files_to_remove, open_zip_job.db.db_id)

        for open_zip_job, _e in report.get_failed_jobs(OpenZipContentsJob):
            box.add_failed_files(open_zip_job.files_to_unzip)

        if self._local_store is None:
            logger.bench('OnlineImporter could not progress without loaded store.')
            return local_store_err

        local_store = self._local_store

        write_stores = {}
        read_stores = {}
        stores = []
        for db in db_pkgs:
            store = local_store.store_by_id(db.db_id)
            write_stores[db.db_id] = store.write_only()
            read_stores[db.db_id] = store.read_only()
            stores.append(store)

        for db_entity, config, db_hash, db_size in box.installed_db_sigs():
            write_stores[db_entity.db_id].set_db_state_signature(db_hash, db_size, db_entity.timestamp, config['filter'])

        for db_id, zip_id in box.removed_zips():
            write_stores[db_id].remove_zip_id(zip_id)

        fs = self._worker_ctx.file_system

        if len(files_to_consume := box.consume_files()) > 0:
            logger.bench('OnlineImporter files_to_consume start.')
            processed_file_names: set[str] = {file_pkg.rel_path for file_pkgs, db_id in box.non_duplicated_files() for file_pkg in file_pkgs}
            processed_files: dict[str, list[PathPackage]] = defaultdict(list)
            removed_files: list[tuple[PathPackage, set[str]]] = []

            for pkg, dbs in files_to_consume:
                for db_id in dbs:
                    if pkg.rel_path in processed_file_names: continue
                    for is_external, drive in read_stores[db_id].list_other_drives_for_file(pkg.rel_path, pkg.drive):
                        file_path = os.path.join(drive, pkg.rel_path)
                        if fs.is_file(file_path):
                            fs.unlink(file_path)

                for db_id in dbs:
                    write_stores[db_id].remove_file(pkg.rel_path)
                    write_stores[db_id].remove_file_from_zips(pkg.rel_path)

                if pkg.rel_path in processed_file_names: continue
                if pkg.is_pext_external():
                    full_path = os.path.join(self._worker_ctx.config['base_path'], pkg.rel_path)
                    if fs.is_file(full_path):
                        fs.unlink(full_path)

                fs.unlink(pkg.full_path)
                processed_files[list(dbs)[0]].append(pkg)
                processed_file_names.add(pkg.rel_path)
                removed_files.append((pkg, dbs))

            box.add_removed_files(removed_files)
            logger.bench('OnlineImporter files_to_consume done.')
        else:
            processed_files = {}

        if len(duplicated_files := box.duplicated_files()) > 0:
            logger.bench('OnlineImporter calculating db_id_by_rel_path start.')
            db_id_by_rel_path = {file_pkg.rel_path: db_id for file_pkgs, db_id in box.non_duplicated_files() for file_pkg in file_pkgs} | \
                                {file_pkg.rel_path: db_id for db_id, file_pkgs in processed_files.items() for file_pkg in file_pkgs}
            logger.bench('OnlineImporter calculating db_id_by_rel_path done.')

            for duplicates, db_id in duplicated_files:
                logger.print(f'Warning! {len(duplicates)} duplicates found in [{db_id}]:')
                for file in duplicates:
                    logger.print(f'DUPLICATED: {file} [using {db_id_by_rel_path[file]} instead]')

        for pkg, dbs in sorted(box.consume_directories(), key=lambda x: len(x[0].full_path), reverse=True):
            if box.is_folder_installed(pkg.rel_path):
                # If a folder got installed by any db...
                # assert len(dbs) >=1
                # The for-loop is for when two+ dbs used to have the same folder but one of them has removed it, it should be kept because
                # one db still uses it. But it should be removed from the store in the other dbs.
                for db_id in dbs:
                    write_stores[db_id].remove_local_folder(pkg.rel_path)
                    write_stores[db_id].remove_local_folder_from_zips(pkg.rel_path)
                continue

            if fs.folder_has_items(pkg.full_path):
                continue

            for db_id in dbs:
                for is_external, drive in read_stores[db_id].list_other_drives_for_folder(pkg):
                    if is_external:
                        # @TODO: This count part blow is for checking if previously it was previously stored as "is_pext_external_subfolder", but since this information is lost, we need to do this. When we store "path" = "pext" we will have this information again, so we can do this much cleaner.
                        if pkg.rel_path.count('/') >= 2 and pkg.rel_path.count('/') >= 2 \
                                and not fs.folder_has_items(full_ext_path := os.path.join(drive, pkg.rel_path)):
                            write_stores[db_id].remove_external_folder(drive, pkg.rel_path)
                            write_stores[db_id].remove_external_folder_from_zips(drive, pkg.rel_path)
                            fs.remove_folder(full_ext_path)
                    else:
                        if not fs.folder_has_items(full_ext_path := os.path.join(drive, pkg.rel_path)):
                            fs.remove_folder(full_ext_path)
                            write_stores[db_id].remove_local_folder(pkg.rel_path)
                            write_stores[db_id].remove_local_folder_from_zips(pkg.rel_path)

                if pkg.is_pext_external() and pkg.drive is not None:
                    if not pkg.is_pext_external_subfolder() and not pkg.is_pext_parent():
                        fs.remove_folder(pkg.full_path)
                        write_stores[db_id].remove_external_folder(pkg.drive, pkg.rel_path)
                        write_stores[db_id].remove_external_folder_from_zips(pkg.drive, pkg.rel_path)
                    full_path = os.path.join(self._worker_ctx.config['base_path'], pkg.rel_path)
                    if fs.is_folder(full_path) and not fs.folder_has_items(full_path):
                        fs.remove_folder(full_path)
                else:
                    fs.remove_folder(pkg.full_path)
                    write_stores[db_id].remove_local_folder(pkg.rel_path)
                    write_stores[db_id].remove_local_folder_from_zips(pkg.rel_path)

        for db_id, file_pkgs in box.installed_file_pkgs().items():
            for file_pkg in file_pkgs:
                if 'reboot' in file_pkg.description and file_pkg.description['reboot'] == True:
                    self._box.set_needs_reboot(True)
                write_stores[db_id].add_file_pkg(file_pkg, file_pkg.rel_path in box.repeated_store_presence()[db_id])

        for db_id, folder_pkg in box.installed_folders():
            write_stores[db_id].add_folder_pkg(folder_pkg)

        for file_pkg, dbs in box.removed_files():
            for db_id in dbs:
                write_stores[db_id].remove_file_pkg(file_pkg)

        for db_id, folder_pkg in box.removed_folders():
            write_stores[db_id].remove_folder_pkg(folder_pkg)

        for db_id, zip_id, zip_summary, zip_description in box.installed_zip_summary():
            write_stores[db_id].add_zip_summary(zip_id, zip_summary, zip_description)

        for db_id, filtered_zip_data in box.filtered_zip_data().items():
            write_stores[db_id].save_filtered_zip_data(filtered_zip_data)

        for w_store in write_stores.values():
            w_store.cleanup_externals()

        self._box.set_needs_save(local_store.needs_save())

        for store in stores:
            self._clean_store(store.unwrap_store())

        for wrong_db_opts_err in box.wrong_db_options():
            self._worker_ctx.swallow_error(wrong_db_opts_err)

        logger.bench('OnlineImporter end.')
        return None

    def save_local_store(self) -> Optional[Exception]:
        if self._local_store is None:
            return None
        self._worker_ctx.logger.bench('OnlineImporter saving local store start.')
        err = self._worker_ctx.local_repository.save_store(self._local_store)
        self._worker_ctx.logger.bench('OnlineImporter saving local store end.')
        return err

    @staticmethod
    def _clean_store(store) -> None:
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

    def box(self) -> 'InstallationBox':
        return self._box


def is_system_path(description: dict[str, str]) -> bool:
    return 'path' in description and description['path'] == 'system'


class InstallationBox:
    def __init__(self) -> None:
        self._downloaded_files: list[str] = []
        self._validated_files: dict[str, list[PathPackage]] = defaultdict(list)  # @TODO: Remove this?
        self._present_validated_files: dict[str, list[PathPackage]] = defaultdict(list)
        self._verified_integrity_file_names: list[str] = []
        self._installed_file_pkgs: dict[str, list[PathPackage]] = defaultdict(list)
        self._installed_file_names: list[str] = []
        self._present_not_validated_files: list[str] = []
        self._fetch_started_files: list[str] = []
        self._failed_files: list[str] = []
        self._failed_folders: list[str] = []
        self._failed_zips: list[tuple[str, str]] = []
        self._full_partitions: dict[str, int] = dict()
        self._failed_db_options: list[WrongDatabaseOptions] = []
        self._removed_files: list[tuple[PathPackage, set[str]]] = []
        self._removed_folders: list[tuple[str, PathPackage]] = []
        self._removed_zips: list[tuple[str, str]] = []
        self._skipped_updated_files: dict[str, list[str]] = dict()
        self._filtered_zip_data: dict[str, dict[str, FileFoldersHolder]] = defaultdict(dict)
        self._installed_zip_summary: list[tuple[str, str, StoreFragmentDrivePaths, dict[str, Any]]] = []
        self._installed_folders: list[tuple[str, PathPackage]] = []
        self._installed_folders_set: set[str] = set()
        self._repeated_store_presence: dict[str, set[str]] = defaultdict(set)
        self._directory_removals: dict[str, tuple[PathPackage, set[str]]] = dict()
        self._file_removals: dict[str, tuple[PathPackage, set[str]]] = dict()
        self._installed_dbs: list[DbEntity] = []
        self._installed_db_sigs: list[tuple[DbEntity, Config, str, int]] = []
        self._failed_dbs: set[str] = set()
        self._duplicated_files: list[tuple[list[str], str]] = []
        self._non_duplicated_files: list[tuple[list[PathPackage], str]] = []
        self._unused_filter_tags: list[str] = []
        self._skipped_dbs: list[str] = []
        self._old_pext_paths: set[str] = set()
        self._needs_save: bool = False
        self._needs_reboot: bool = False

    def set_unused_filter_tags(self, tags: list[str]) -> None:
        self._unused_filter_tags = tags
    def set_old_pext_paths(self, paths: set[str]) -> None:
        self._old_pext_paths = paths
    def set_needs_save(self, needs_save: bool) -> None:
        self._needs_save = needs_save
    def set_needs_reboot(self, needs_reboot: bool) -> None:
        self._needs_reboot = needs_reboot
    def add_downloaded_file(self, path: str) -> None:
        self._downloaded_files.append(path)
    def add_downloaded_files(self, files: list[PathPackage]) -> None:
        if len(files) == 0: return
        for pkg in files:
            self._downloaded_files.append(pkg.rel_path)
    def add_validated_file(self, path_pkg: PathPackage, db_id: str) -> None:
        self._validated_files[db_id].append(path_pkg)
        self._installed_file_pkgs[db_id].append(path_pkg)
        self._installed_file_names.append(path_pkg.rel_path)
    def add_validated_files(self, files: list[PathPackage], db_id: str) -> None:
        if len(files) == 0: return
        self._validated_files[db_id].extend(files)
        self._installed_file_pkgs[db_id].extend(files)
        self._installed_file_names.extend(pkg.rel_path for pkg in files)
    def add_repeated_store_presence(self, non_external_store_entries: set[str], db_id: str) -> None:
        self._repeated_store_presence[db_id].update(non_external_store_entries)
    def add_installed_zip_summary(self, db_id: str, zip_id: str, fragment: StoreFragmentDrivePaths, description: dict[str, Any]) -> None:
        self._installed_zip_summary.append((db_id, zip_id, fragment, description))
    def add_present_validated_files(self, paths: list[PathPackage], db_id: str) -> None:
        if len(paths) == 0: return
        self._present_validated_files[db_id].extend(paths)
        self._installed_file_pkgs[db_id].extend(paths)
        self._installed_file_names.extend(pkg.rel_path for pkg in paths)
    def add_verified_integrity_files(self, pkgs: list[PathPackage], _db_id: str) -> None:
        if len(pkgs) == 0: return
        self._verified_integrity_file_names.extend(pkg.rel_path for pkg in pkgs)
    def add_present_not_validated_files(self, paths: list[PathPackage]) -> None:
        if len(paths) == 0: return
        self._present_not_validated_files.extend([p.rel_path for p in paths])
    def add_skipped_updated_files(self, paths: list[PathPackage], db_id: str) -> None:
        if len(paths) == 0: return
        if db_id not in self._skipped_updated_files:
            self._skipped_updated_files[db_id] = []
        self._skipped_updated_files[db_id].extend([p.rel_path for p in paths])
    def add_skipped_db(self, db_id: str) -> None:
        self._skipped_dbs.append(db_id)
    def add_file_fetch_started(self, path: str) -> None:
        self._fetch_started_files.append(path)
    def add_failed_file(self, path: str) -> None:
        self._failed_files.append(path)
    def add_failed_db(self, db_id: str) -> None:
        self._failed_dbs.add(db_id)
    def add_failed_files(self, file_pkgs: list[PathPackage]) -> None:
        if len(file_pkgs) == 0: return
        for pkg in file_pkgs:
            self._failed_files.append(pkg.rel_path)
    def add_duplicated_files(self, files: list[str], db_id: str) -> None:
        if len(files) == 0: return
        self._duplicated_files.append((files, db_id))
    def add_non_duplicated_files(self, files: list[PathPackage], db_id: str) -> None:
        if len(files) == 0: return
        self._non_duplicated_files.append((files, db_id))
    def add_failed_zip(self, db_id: str, zip_id: str) -> None:
        self._failed_zips.append((db_id, zip_id))
    def add_removed_zip(self, db_id: str, zip_id: str) -> None:
        self._removed_zips.append((db_id, zip_id))
    def add_failed_folders(self, folders: list[str]) -> None:
        self._failed_folders.extend(folders)
    def add_full_partitions(self, full_partitions: list[tuple[Partition, int]]) -> None:
        if len(full_partitions) == 0: return
        for partition, failed_reserve in full_partitions:
            if partition.path not in self._full_partitions:
                self._full_partitions[partition.path] = failed_reserve
            else:
                self._full_partitions[partition.path] += failed_reserve
    def add_installed_db(self, db: DbEntity, config: Config, db_hash: str, db_size: int) -> None:
        self._installed_dbs.append(db)
        self._installed_db_sigs.append((db, config, db_hash, db_size))
    def add_filtered_zip_data(self, db_id: str, zip_id: str, filtered_data: FileFoldersHolder) -> None:
        self._filtered_zip_data[db_id][zip_id] = filtered_data
    def add_failed_db_options(self, exception: WrongDatabaseOptions) -> None:
        self._failed_db_options.append(exception)
    def add_removed_files(self, files: list[tuple[PathPackage, set[str]]]) -> None:
        if len(files) == 0: return
        self._removed_files.extend(files)
    def add_removed_folders(self, folders: list[PathPackage], db_id: str) -> None:
        if len(folders) == 0: return
        self._removed_folders.extend([(db_id, pkg) for pkg  in folders])
    def add_installed_folders(self, folders: list[PathPackage], db_id: str) -> None:
        if len(folders) == 0: return
        self._installed_folders.extend([(db_id, pkg) for pkg in folders])
        self._installed_folders_set.update([pkg.rel_path for pkg in folders])

    def is_folder_installed(self, path: str) -> bool:  return path in self._installed_folders_set
    def downloaded_files(self): return self._downloaded_files
    def present_validated_files(self) -> list[str]: return [pkg.rel_path for path_pkgs in self._present_validated_files.values() for pkg in path_pkgs]
    def verified_integrity_files(self) -> list[str]: return self._verified_integrity_file_names
    def present_not_validated_files(self): return self._present_not_validated_files
    def fetch_started_files(self): return self._fetch_started_files
    def failed_files(self): return self._failed_files
    def duplicated_files(self): return self._duplicated_files
    def non_duplicated_files(self): return self._non_duplicated_files
    def failed_folders(self): return self._failed_folders
    def failed_zips(self): return self._failed_zips
    def removed_files(self): return self._removed_files
    def removed_folders(self): return self._removed_folders
    def removed_zips(self): return self._removed_zips
    def installed_file_pkgs(self): return self._installed_file_pkgs
    def installed_file_names(self): return self._installed_file_names
    def installed_folders(self): return self._installed_folders
    def wrong_db_options(self): return self._failed_db_options
    def repeated_store_presence(self): return self._repeated_store_presence
    def installed_zip_summary(self): return self._installed_zip_summary
    def skipped_updated_files(self): return self._skipped_updated_files
    def filtered_zip_data(self): return self._filtered_zip_data
    def full_partitions(self) -> dict[str, int]: return self._full_partitions
    def installed_db_sigs(self): return self._installed_db_sigs
    def installed_dbs(self) -> list[DbEntity]: return self._installed_dbs
    def updated_dbs(self) -> list[str]: return list(self._validated_files)
    def failed_dbs(self) -> list[str]: return list(self._failed_dbs)
    def unused_filter_tags(self): return self._unused_filter_tags
    def skipped_dbs(self): return self._skipped_dbs
    def old_pext_paths(self) -> set[str]: return self._old_pext_paths
    def needs_save(self) -> bool: return self._needs_save
    def needs_reboot(self) -> bool: return self._needs_reboot

    def queue_directory_removal(self, dirs: list[PathPackage], db_id: str) -> None:
        if len(dirs) == 0: return
        for pkg in dirs:
            if pkg.rel_path not in self._directory_removals:
                self._directory_removals[pkg.rel_path] = (pkg, set())
            self._directory_removals[pkg.rel_path][1].add(db_id)
    def queue_file_removal(self, files: list[PathPackage], db_id: str) -> None:
        if len(files) == 0: return
        for pkg in files:
            if pkg.rel_path not in self._file_removals:
                self._file_removals[pkg.rel_path] = (pkg, set())
            self._file_removals[pkg.rel_path][1].add(db_id)

    def consume_files(self) -> list[tuple[PathPackage, set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._file_removals.values()], key=lambda x: x[0].rel_path)
        self._file_removals.clear()
        return result

    def consume_directories(self) -> list[tuple[PathPackage, set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._directory_removals.values()], key=lambda x: len(x[0].rel_path))
        self._directory_removals.clear()
        return result


class NetworkProblems(DownloaderError): pass
