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

import sys
from typing import Optional, Any, Iterable
from collections import defaultdict
import os

from downloader.constants import FILE_MiSTer
from downloader.db_entity import DbEntity, make_db_tag
from downloader.db_utils import DbSectionPackage
from downloader.job_system import Job, JobSystem
from downloader.jobs.errors import WrongDatabaseOptions
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.jobs_factory import make_get_data_job
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.reporters import ProcessedFile
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.jobs.workers_factory import make_workers
from downloader.logger import Logger
from downloader.file_filter import BadFileFilterPartException, FileFoldersHolder
from downloader.free_space_reservation import FreeSpaceReservation, Partition
from downloader.job_system import JobSystem
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.local_store_wrapper import LocalStoreWrapper, StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType, RemovedCopy


class OnlineImporter:
    def __init__(self, logger: Logger, job_system: JobSystem, worker_ctx: DownloaderWorkerContext, free_space_reservation: FreeSpaceReservation):
        self._logger = logger
        self._job_system = job_system
        self._worker_ctx = worker_ctx
        self._free_space_reservation = free_space_reservation
        self._local_store: Optional[LocalStoreWrapper] = None
        self._box = InstallationBox()
        self._needs_reboot = False
        self._needs_save = False

    def _make_workers(self) -> dict[int, DownloaderWorker]:
        return {w.job_type_id(): w for w in make_workers(self._worker_ctx)}

    def _make_jobs(self, db_pkgs: list[DbSectionPackage], local_store: LocalStoreWrapper, full_resync: bool) -> list[Job]:
        jobs: list[Job] = []
        for pkg in db_pkgs:
            # @TODO: Use proper tempfile.mkstemp instead
            fetch_data_job = make_get_data_job(pkg.section['db_url'], {}, self._logger)
            fetch_data_job.after_job = OpenDbJob(
                transfer_job=fetch_data_job,
                section=pkg.db_id,
                ini_description=pkg.section,
                store=local_store.store_by_id(pkg.db_id),
                full_resync=full_resync,
            )
            db_tag = make_db_tag(pkg.db_id)
            fetch_data_job.add_tag(db_tag)
            fetch_data_job.after_job.add_tag(db_tag)
            jobs.append(fetch_data_job)
        return jobs

    def set_local_store(self, local_store: LocalStoreWrapper) -> None:
        self._local_store = local_store

    def download_dbs_contents(self, db_pkgs: list[DbSectionPackage], full_resync: bool):
        if self._local_store is None: raise Exception("Local store is not set")

        logger = self._logger
        logger.bench('OnlineImporter start.')
        
        local_store: LocalStoreWrapper = self._local_store

        self._job_system.register_workers(self._make_workers())
        self._job_system.push_jobs(self._make_jobs(db_pkgs, local_store, full_resync))

        logger.bench('OnlineImporter execute jobs start.')
        self._job_system.execute_jobs()
        logger.bench('OnlineImporter execute jobs done.')

        box = self._box
        report = self._worker_ctx.file_download_session_logger.report()

        box.set_unused_filter_tags(self._worker_ctx.file_filter_factory.unused_filter_parts())

        for db in db_pkgs:
            changes = len(report.get_jobs_completed_by_tag(db.db_id))
            if changes > 0:
                box.add_updated_db(db.db_id)

            failures = len(report.get_jobs_failed_by_tag(make_db_tag(db.db_id)))
            if failures > 0:
                box.add_failed_db(db.db_id)

        for job in report.get_completed_jobs(ProcessDbMainJob):
            box.add_installed_db(job.db)
            for zip_id in job.ignored_zips:
                box.add_failed_zip(job.db.db_id, zip_id)
            for zip_id in job.removed_zips:
                box.add_removed_zip(job.db.db_id, zip_id)

        for job, _e in report.get_failed_jobs(ProcessDbMainJob):
            box.add_failed_db(job.db.db_id)

        for job in report.get_completed_jobs(ProcessDbIndexJob):
            box.add_present_not_validated_files(job.present_not_validated_files)
            box.add_duplicated_files(job.duplicated_files, job.db.db_id)
            box.add_processed_files(job.non_duplicated_files, job.db.db_id)
            box.add_present_validated_files(job.present_validated_files)
            box.add_skipped_updated_files(job.skipped_updated_files, job.db.db_id)
            box.add_removed_copies(job.removed_folders)
            box.add_installed_folders(job.installed_folders)
            box.queue_directory_removal(job.directories_to_remove, job.db.db_id)
            box.queue_file_removal(job.files_to_remove, job.db.db_id)

        for job, e in report.get_failed_jobs(ProcessDbIndexJob):
            box.add_full_partitions(job.full_partitions)
            box.add_failed_files(job.failed_files_no_space)
            box.add_failed_folders(job.failed_folders)
            if not isinstance(e, BadFileFilterPartException): continue
            box.add_failed_db_options(WrongDatabaseOptions(f"Wrong custom download filter on database {job.db.db_id}. Part '{str(e)}' is invalid."))

        for job in report.get_completed_jobs(ProcessZipIndexJob):
            box.add_present_not_validated_files(job.present_not_validated_files)
            box.add_duplicated_files(job.duplicated_files, job.db.db_id)
            box.add_processed_files(job.non_duplicated_files, job.db.db_id)
            box.add_present_validated_files(job.present_validated_files)
            box.add_skipped_updated_files(job.skipped_updated_files, job.db.db_id)
            box.add_removed_copies(job.removed_folders)
            box.add_installed_folders(job.installed_folders)
            box.queue_directory_removal(job.directories_to_remove, job.db.db_id)
            box.queue_file_removal(job.files_to_remove, job.db.db_id)
            if job.summary_download_failed is not None:
                box.add_failed_file(job.summary_download_failed)
            if job.filtered_data:
                box.add_filtered_zip_data(job.db.db_id, job.zip_id, job.filtered_data)
            if job.has_new_zip_summary:
                box.add_installed_zip_summary(job.db.db_id, job.zip_id, job.result_zip_index, job.zip_description)

        for job, _e in report.get_failed_jobs(ProcessZipIndexJob):
            if job.summary_download_failed is not None:
                box.add_failed_file(job.summary_download_failed)
            box.add_failed_files(job.failed_files_no_space)
            box.add_full_partitions(job.full_partitions)
            box.add_failed_folders(job.failed_folders)

        for job in report.get_completed_jobs(OpenZipContentsJob):
            box.add_downloaded_files(job.downloaded_files)
            box.add_validated_files(job.validated_files)
            # We should be able to comment previous line and the test still pass
            box.add_failed_files(job.failed_files)
            box.queue_directory_removal(job.directories_to_remove, job.db.db_id)
            box.queue_file_removal(job.files_to_remove, job.db.db_id)

        for job, _e in report.get_failed_jobs(OpenZipContentsJob):
            box.add_failed_files(job.files_to_unzip)

        for job in report.get_started_jobs(FetchFileJob):
            box.add_file_fetch_started(job.info)

        for job in report.get_completed_jobs(FetchFileJob) + report.get_completed_jobs(CopyFileJob):
            if job.silent: continue
            box.add_downloaded_file(job.info)

        for job, _e in report.get_failed_jobs(FetchFileJob) + report.get_failed_jobs(CopyFileJob):
            box.add_failed_file(job.info)

        for job in report.get_completed_jobs(ValidateFileJob):
            if job.after_job is not None: continue
            box.add_validated_file(job.info)

        for job, _e in report.get_failed_jobs(FetchDataJob):
            box.add_failed_file(job.source)  # @TODO: This should not count as a file, but as a "source".

        for job, e in report.get_failed_jobs(ValidateFileJob):
            box.add_failed_file(job.get_file_job.info)
            if job.info != FILE_MiSTer:
                continue

            self._logger.debug(e)
            fs = self._worker_ctx.file_system
            if fs.is_file(job.target_file_path, use_cache=False):
                continue

            if fs.is_file(job.backup_path, use_cache=False):
                fs.move(job.backup_path, job.target_file_path)
            elif fs.is_file(job.temp_path, use_cache=False) and fs.hash(job.temp_path) == job.description['hash']:
                fs.move(job.temp_path, job.target_file_path)

            if fs.is_file(job.target_file_path, use_cache=False):
                continue

            # This error message should never happen.
            # If it happens it would be an unexpected case where file_system is not moving files correctly
            self._logger.print('CRITICAL ERROR!!! Could not restore the MiSTer binary!')
            self._logger.print('Please manually rename the file MiSTer.new as MiSTer')
            self._logger.print('Your system won\'nt be able to boot until you do so!')
            sys.exit(1)

        logger.bench('OnlineImporter applying changes on stores...')

        for duplicates, db_id in box.duplicated_files():
            self._logger.print(f'Warning! {len(duplicates)} duplicates found in [{db_id}]:')
            for file in duplicates:
                self._logger.print(f'DUPLICATED: {file} [using {box.processed_file(file).db_id} instead]')

        stores = {}
        for db in db_pkgs:
            stores[db.db_id] = local_store.store_by_id(db.db_id)

        for db_id, zip_id in box.removed_zips():
            stores[db_id].write_only().remove_zip_id(zip_id)

        removed_files = []
        processed_files = defaultdict(list)
        for pkg, dbs in box.consume_files():
            for db_id in dbs:
                stores[db_id].write_only().remove_file(pkg.rel_path)
                stores[db_id].write_only().remove_file_from_zips(pkg.rel_path)

            if box.is_file_processed(pkg.rel_path): continue

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
            box.add_processed_files(pkgs, db_id)

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

            if not pkg.is_pext_external_subfolder():
                self._worker_ctx.file_system.remove_folder(pkg.full_path)

            for db_id in dbs:
                stores[db_id].write_only().remove_folder(pkg.rel_path)
                stores[db_id].write_only().remove_folder_from_zips(pkg.rel_path)

        external_parents_by_db: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        parents_by_db: dict[str, set[str]] = defaultdict(set)

        def add_parent(el_pkg: PathPackage, db_id: str) -> None:
            if el_pkg.pext_props is not None:
                if el_pkg.is_pext_standard():
                    parents_by_db[db_id].add(el_pkg.pext_props.parent)
                else:
                    external_parents_by_db[db_id][el_pkg.pext_props.parent].add(el_pkg.pext_props.drive)

        for file_path in box.installed_files():
            file = box.processed_file(file_path)
            if 'reboot' in file.pkg.description and file.pkg.description['reboot'] == True:
                self._needs_reboot = True

            add_parent(file.pkg, file.db_id)
    
        for file_path in box.present_not_validated_files() + box.installed_files():
            file = box.processed_file(file_path)

            for is_external, other_drive in stores[file.db_id].read_only().list_other_drives_for_file(file.pkg.rel_path, file.pkg.pext_drive()):
                other_file = os.path.join(other_drive, file.pkg.rel_path)
                if not self._worker_ctx.file_system.is_file(other_file):
                    if is_external:
                        stores[file.db_id].write_only().remove_external_file(other_drive, file.pkg.rel_path)
                    else:
                        stores[file.db_id].write_only().remove_local_file(file.pkg.rel_path)

            stores[file.db_id].write_only().add_file_pkg(file.pkg)

            if file.pkg.pext_props is not None:
                for other in file.pkg.pext_props.other_drives:
                    if self._worker_ctx.file_system.is_file(os.path.join(other, file.pkg.rel_path)):
                        stores[file.db_id].write_only().add_external_file(other, file.pkg.rel_path, file.pkg.description)

        # for file_path in box.failed_files():
        #     if not report.is_file_processed(file_path):
        #         continue
        #     file = box.processed_file(file_path)
        #     stores[file.db_id].write_only().remove_file(file.pkg.rel_path)

        for folder_path in sorted(box.installed_folders(), key=lambda x: len(x), reverse=True):
            for db_id, folder_pkg in report.processed_folder(folder_path).items():
                if folder_pkg.is_pext_parent():
                    continue

                stores[db_id].write_only().add_folder_pkg(folder_pkg)
                add_parent(folder_pkg, db_id)

        for folder_path in sorted(box.installed_folders(), key=lambda x: len(x), reverse=True):
            for db_id, folder_pkg in report.processed_folder(folder_path).items():
                if not folder_pkg.is_pext_parent():
                    continue

                if folder_pkg.pext_props.parent in parents_by_db[db_id]:
                    stores[db_id].write_only().add_folder(folder_pkg.rel_path, folder_pkg.description)
                if folder_pkg.pext_props.parent in external_parents_by_db[db_id]:
                    for drive in external_parents_by_db[db_id][folder_pkg.pext_props.parent]:
                        stores[db_id].write_only().add_external_folder(drive, folder_pkg.rel_path, folder_pkg.description)

        for file_path in box.removed_files():
            file = box.processed_file(file_path)
            stores[file.db_id].write_only().remove_file(file.pkg.rel_path)

        for is_external, el_path, drive, ty in box.removed_copies():
            if ty == PathType.FILE:
                file = box.processed_file(el_path)
                if is_external:
                    stores[file.db_id].write_only().remove_external_file(drive, el_path)
                else:
                    stores[file.db_id].write_only().remove_local_file(el_path)

            elif ty == PathType.FOLDER:
                for db_id, folder_pkg in report.processed_folder(el_path).items():
                    if is_external:
                        stores[db_id].write_only().remove_external_folder(drive, el_path)
                    else:
                        stores[db_id].write_only().remove_local_folder(el_path)

        for db_id, zip_id, zip_summary, zip_description in box.installed_zip_summary():
            stores[db_id].write_only().add_zip_summary(zip_id, zip_summary, zip_description)

        filtered_zip_data = {}
        for db_id, zip_id, files, folders in box.filtered_zip_data():
            if db_id not in filtered_zip_data:
                filtered_zip_data[db_id] = {}

            if zip_id not in filtered_zip_data[db_id]:
                filtered_zip_data[db_id][zip_id] = {'files': {}, 'folders': {}}

            filtered_zip_data[db_id][zip_id]['files'].update(files)
            filtered_zip_data[db_id][zip_id]['folders'].update(folders)

        for db_id, filtered_zip_data_by_db in filtered_zip_data.items():
            stores[db_id].write_only().save_filtered_zip_data(filtered_zip_data_by_db)

        for store in stores.values():
            store.write_only().cleanup_externals()

        self._needs_save = local_store.needs_save()

        for store in stores.values():
            self._clean_store(store.unwrap_store())

        for e in box.wrong_db_options():
            self._worker_ctx.swallow_error(e)

        logger.bench('OnlineImporter done.')
        return self
 
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

    def folders_that_failed(self) -> list[str]:
        return self._box.failed_folders()

    def zips_that_failed(self) -> list[str]:
        return [f'{db_id}:{zip_id}' for db_id, zip_id in self._box.failed_zips()]

    def files_that_failed(self):
        return self._box.failed_files()

    def box(self) -> 'InstallationBox':
        return self._box

    def dbs_that_failed(self):
        return self._box.failed_dbs()

    def new_files_not_overwritten(self):
        return self._box.skipped_updated_files()

    def needs_reboot(self):
        return self._needs_reboot

    def full_partitions(self):
        return [p for p, s in self._box.full_partitions().items()]

    def free_space(self):
        actual_remaining_space = dict(self._free_space_reservation.free_space())
        for p, reservation in self._box.full_partitions().items():
            actual_remaining_space[p] -= reservation
        return actual_remaining_space

    def correctly_downloaded_dbs(self) -> list[DbEntity]:
        return self._box.installed_dbs()

    def correctly_installed_files(self):
        return self._box.installed_files()

    def run_files(self):
        return self._box.fetch_started_files()

    @property
    def needs_save(self) -> bool:
        return self._needs_save


def is_system_path(description: dict[str, str]) -> bool:
    return 'path' in description and description['path'] == 'system'


class InstallationBox:
    def __init__(self):
        self._downloaded_files: list[str] = []
        self._validated_files: list[str] = []
        self._present_validated_files: list[str] = []
        self._present_not_validated_files: list[str] = []
        self._fetch_started_files: list[str] = []
        self._failed_files: list[str] = []
        self._failed_folders: list[str] = []
        self._failed_zips: list[tuple[str, str]] = []
        self._full_partitions: dict[str, int] = dict()
        self._failed_db_options: list[WrongDatabaseOptions] = []
        self._removed_files: list[str] = []
        self._removed_copies: list[RemovedCopy] = []
        self._removed_zips: list[tuple[str, str]] = []
        self._skipped_updated_files: dict[str, list[str]] = dict()
        self._filtered_zip_data: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
        self._installed_zip_summary: list[tuple[str, str, StoreFragmentDrivePaths, dict[str, Any]]] = []
        self._installed_folders: set[str] = set()
        self._directories = dict()
        self._files = dict()
        self._installed_dbs: list[DbEntity] = []
        self._updated_dbs: list[str] = []
        self._failed_dbs: list[str] = []
        self._duplicated_files: list[tuple[list[str], str]] = []
        self._processed_files: dict[str, ProcessedFile] = dict()
        self._unused_filter_tags: list[str] = []

    def set_unused_filter_tags(self, tags: list[str]):
        self._unused_filter_tags = tags
    def add_downloaded_file(self, path: str):
        self._downloaded_files.append(path)
    def add_downloaded_files(self, files: list[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._downloaded_files.append(pkg.rel_path)
    def add_validated_file(self, path: str):
        self._validated_files.append(path)
    def add_validated_files(self, files: list[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._validated_files.append(pkg.rel_path)
    def add_installed_zip_summary(self, db_id: str, zip_id: str, fragment: StoreFragmentDrivePaths, description: dict[str, Any]):
        self._installed_zip_summary.append((db_id, zip_id, fragment, description))
    def add_present_validated_files(self, paths: list[PathPackage]):
        if len(paths) == 0: return
        self._present_validated_files.extend([p.rel_path for p in paths])
    def add_present_not_validated_files(self, paths: list[PathPackage]):
        if len(paths) == 0: return
        self._present_not_validated_files.extend([p.rel_path for p in paths])
    def add_skipped_updated_files(self, paths: list[PathPackage], db_id: str):
        if len(paths) == 0: return
        if db_id not in self._skipped_updated_files:
            self._skipped_updated_files[db_id] = []
        self._skipped_updated_files[db_id].extend([p.rel_path for p in paths])
    def add_file_fetch_started(self, path: str):
        self._fetch_started_files.append(path)
    def add_failed_file(self, path: str):
        self._failed_files.append(path)
    def add_failed_db(self, db_id: str):
        self._failed_dbs.append(db_id)
    def add_failed_files(self, file_pkgs: list[PathPackage]):
        if len(file_pkgs) == 0: return
        for pkg in file_pkgs:
            self._failed_files.append(pkg.rel_path)
    def add_processed_files(self, pkgs: list[PathPackage], db_id: str):
        self._processed_files.update({p.rel_path: ProcessedFile(p, db_id) for p in pkgs})
    def add_duplicated_files(self, files: list[str], db_id: str):
        if len(files) == 0: return
        self._duplicated_files.append((files, db_id))
    def add_failed_zip(self, db_id: str, zip_id: str):
        self._failed_zips.append((db_id, zip_id))
    def add_removed_zip(self, db_id: str, zip_id: str):
        self._removed_zips.append((db_id, zip_id))
    def add_failed_folders(self, folders: list[str]):
        self._failed_folders.extend(folders)
    def add_full_partitions(self, full_partitions: list[tuple[Partition, int]]):
        if len(full_partitions) == 0: return
        for partition, failed_reserve in full_partitions:
            if partition.path not in self._full_partitions:
                self._full_partitions[partition.path] = failed_reserve
            else:
                self._full_partitions[partition.path] += failed_reserve
    def add_installed_db(self, db: DbEntity):
        self._installed_dbs.append(db)
    def add_updated_db(self, db_id: str):
        self._updated_dbs.append(db_id)
    def add_filtered_zip_data(self, db_id: str, zip_id: str, filtered_data: FileFoldersHolder) -> None:
        files, folders = filtered_data['files'], filtered_data['folders']
        #if len(files) == 0 and len(folders) == 0: return
        self._filtered_zip_data.append((db_id, zip_id, files, folders))
    def add_failed_db_options(self, exception: WrongDatabaseOptions):
        self._failed_db_options.append(exception)
    def add_removed_file(self, file: str):
        self._removed_files.append(file)
    def add_removed_files(self, files: list[PathPackage]):
        if len(files) == 0: return
        for pkg in files:
            self._removed_files.append(pkg.rel_path)
    def add_removed_copies(self, copies: list[RemovedCopy]):
        if len(copies) == 0: return
        self._removed_copies.extend(copies)
    def add_installed_folders(self, folders: list[PathPackage]):
        if len(folders) == 0: return
        for pkg in folders:
            self._installed_folders.add(pkg.rel_path)

    def is_folder_installed(self, path: str) -> bool:  return path in self._installed_folders
    def downloaded_files(self): return self._downloaded_files
    def present_validated_files(self): return self._present_validated_files
    def present_not_validated_files(self): return self._present_not_validated_files
    def fetch_started_files(self): return self._fetch_started_files
    def failed_files(self): return self._failed_files
    def duplicated_files(self): return self._duplicated_files
    def failed_folders(self): return self._failed_folders
    def failed_zips(self): return self._failed_zips
    def removed_files(self): return self._removed_files
    def removed_copies(self): return self._removed_copies
    def removed_zips(self): return self._removed_zips
    def installed_files(self): return list(set(self._present_validated_files) | set(self._validated_files))
    def installed_folders(self): return list(self._installed_folders)
    def uninstalled_files(self): return self._removed_files + self._failed_files
    def wrong_db_options(self): return self._failed_db_options
    def installed_zip_summary(self): return self._installed_zip_summary
    def skipped_updated_files(self): return self._skipped_updated_files
    def filtered_zip_data(self): return self._filtered_zip_data
    def full_partitions(self) -> dict[str, int]: return self._full_partitions
    def installed_dbs(self) -> list[DbEntity]: return self._installed_dbs
    def updated_dbs(self) -> list[str]: return self._updated_dbs
    def failed_dbs(self) -> list[str]: return self._failed_dbs
    def unused_filter_tags(self): return self._unused_filter_tags
    def is_file_processed(self, path: str) -> bool: return path in self._processed_files
    def processed_file(self, path: str) -> ProcessedFile: return self._processed_files[path]
    def all_processed_files(self) -> list[str]: return list(self._processed_files.keys())

    def queue_directory_removal(self, dirs: list[PathPackage], db_id: str) -> None:
        if len(dirs) == 0: return
        for pkg in dirs:
            self._directories.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)
    def queue_file_removal(self, files: list[PathPackage], db_id: str) -> None:
        if len(files) == 0: return
        for pkg in files:
            self._files.setdefault(pkg.rel_path, (pkg, set()))[1].add(db_id)

    def consume_files(self) -> list[tuple[PathPackage, set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._files.values()], key=lambda x: x[0].rel_path)
        self._files.clear()
        return result

    def consume_directories(self) -> list[tuple[PathPackage, set[str]]]:
        result = sorted([(x[0], x[1]) for x in self._directories.values()], key=lambda x: len(x[0].rel_path))
        self._directories.clear()
        return result
    