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

from typing import Dict, Any, List
from pathlib import Path

from downloader.constants import PathType
from downloader.db_entity import DbEntity
from downloader.file_filter import FileFilterFactory, BadFileFilterPartException
from downloader.jobs.index import Index
from downloader.jobs.path_package import PathPackage
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.file_system import FileCopyError
from downloader.storage_priority_resolver import StoragePriorityError
from downloader.target_path_calculator import TargetPathsCalculator


class OpenZipContentsWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)

    def job_type_id(self) -> int: return OpenZipContentsJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenZipContentsJob):
        try:
            kind = job.zip_description.get('kind', None)
            if kind == 'extract_all_contents':
                self._extract_all_contents(job)
            elif kind == 'extract_single_files':
                self._extract_single_files(job)
            else:
                # @TODO: Handle this case, it should never raise in any case
                raise Exception(f"Unknown kind '{kind}' for zip '{job.zip_id}' in db '{job.db.db_id}'")
        except BadFileFilterPartException as e:
            return e
        except StoragePriorityError as e:
            return e

    def _extract_all_contents(self, job: OpenZipContentsJob):
        db = job.db
        config = job.config
        zip_description = job.zip_description
        download_path = job.download_path
        store = job.store.read_only()

        self._ctx.logger.print(zip_description['description'])

        target_folder_path = self._ctx.target_paths_calculator_factory\
            .target_paths_calculator(config)\
            .deduce_target_path(zip_description['target_folder_path'], {}, PathType.FOLDER)

        for pkg in job.folders:
            if self._ctx.file_system.is_folder(pkg.full_path):
                continue

            self._ctx.file_system.make_dirs(pkg.full_path)
            job.store.write_only().add_folder(pkg.rel_path, pkg.description)
            self._ctx.installation_report.add_installed_folder(pkg.rel_path)

        # @TODO: self._ctx.file_system.precache_is_file_with_folders() THIS IS MISSING FOR PROPER PERFORMANCE!
        contained_files = []
        for pkg in job.files:
            file_hash = store.hash_file(pkg.rel_path)
            pkg_hash = pkg.description.get('hash', None)
            is_file_present = self._ctx.file_system.is_file(pkg.full_path)

            if file_hash != pkg_hash or not is_file_present:
                contained_files.append(pkg)

        if len(contained_files) > 0:
            self._ctx.file_system.unzip_contents(download_path, target_folder_path, [pkg.full_path for pkg in contained_files])

        self._ctx.file_system.unlink(download_path)

        for file_path, file_description in job.filtered_data['files'].items():
            self._ctx.pending_removals.queue_file_removal(PathPackage(full_path=file_path, rel_path=file_path, description=file_description), db.db_id)

        for folder_path, folder_description in job.filtered_data['folders'].items():
            self._ctx.pending_removals.queue_directory_removal(PathPackage(full_path=folder_path, rel_path=folder_path, description=folder_description), db.db_id)

        for pkg in contained_files:
            job.downloaded_files.append(pkg.rel_path)

    def _extract_single_files(self, job: OpenZipContentsJob):
        zip_id = job.zip_id
        zip_description = job.zip_description
        download_path = job.download_path
        store = job.store.read_only()
        files = job.files

        self._ctx.logger.print(zip_description['description'])

        temp_filename = self._ctx.file_system.unique_temp_filename()
        tmp_path = f'{temp_filename.value}_{zip_id}'

        # @TODO: self._ctx.file_system.precache_is_file_with_folders() THIS IS MISSING FOR PROPER PERFORMANCE!

        contained_files = [pkg for pkg in files if store.hash_file(pkg.rel_path) != pkg.description.get('hash', None) or self._ctx.file_system.is_file(pkg.full_path) is False]

        if len(contained_files) > 0:
            self._ctx.file_system.unzip_contents(download_path, tmp_path, [pkg.rel_path for pkg in contained_files])

            for pkg in contained_files:
                file_path = pkg.rel_path
                file_description = pkg.description
                try:
                    self._ctx.file_system.copy(str(Path(tmp_path) / Path(file_description['zip_path'])), file_path)
                except FileCopyError as _e:
                    job.failed_files.append(file_path)
                    self._ctx.logger.print('ERROR: File "%s" could not be copied, skipping.' % file_path)
                    continue

                job.downloaded_files.append(file_path)

        self._ctx.file_system.unlink(download_path)
        self._ctx.file_system.remove_non_empty_folder(tmp_path)
        temp_filename.close()
