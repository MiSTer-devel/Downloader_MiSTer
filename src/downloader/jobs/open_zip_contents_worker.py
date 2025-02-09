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

from typing import List, Set
from pathlib import Path

from downloader.db_entity import DbEntity
from downloader.file_filter import BadFileFilterPartException
from downloader.job_system import WorkerResult
from downloader.jobs.index import Index
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.path_package import PathPackage, PathType
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext, DownloaderWorkerFailPolicy
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.file_system import FileCopyError
from downloader.target_path_calculator import StoragePriorityError


class OpenZipContentsWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)

    def job_type_id(self) -> int: return OpenZipContentsJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenZipContentsJob) -> WorkerResult:  # type: ignore[override]
        try:
            kind = job.zip_description.get('kind', None)
            if kind == 'extract_all_contents':
                return self._extract_all_contents(job)
            elif kind == 'extract_single_files':
                return self._extract_single_files(job)
            else:
                # @TODO: Handle this case, it should never raise in any case
                raise Exception(f"Unknown kind '{kind}' for zip '{job.zip_id}' in db '{job.db.db_id}'")
        except BadFileFilterPartException as e:
            return [], e
        except StoragePriorityError as e:
            return [], e

    def _extract_all_contents(self, job: OpenZipContentsJob) -> WorkerResult:
        db = job.db
        config = job.config
        zip_description = job.zip_description
        download_path = job.download_path
        store = job.store.read_only()

        self._ctx.logger.print(zip_description['description'])

        target_pkg, target_error = self._ctx.target_paths_calculator_factory\
            .target_paths_calculator(config)\
            .deduce_target_path(zip_description['target_folder_path'], {}, PathType.FOLDER)

        if target_error is not None:
            if self._ctx.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
                raise target_error

            self._ctx.logger.print(f"ERROR: {target_error}")

        target_folder_path = target_pkg.full_path

        job.installed_folders = self._process_create_folders_packages(db, job.folders)

        # @TODO: self._ctx.file_system.precache_is_file_with_folders() THIS IS MISSING FOR PROPER PERFORMANCE!
        contained_files = []
        for pkg in job.files:
            file_hash = store.hash_file(pkg.rel_path)
            pkg_hash = pkg.description.get('hash', None)
            is_file_present = self._ctx.file_system.is_file(pkg.full_path)

            if file_hash != pkg_hash or not is_file_present:
                contained_files.append(pkg)

        if len(contained_files) > 0:
            self._ctx.installation_report.add_processed_files(contained_files, job.db.db_id)  # @TODO: this needs to be moved to process_zip_worker and as much as possible of the previous lines
            self._logger.print(zip_description['description'])
            self._ctx.file_system.unzip_contents(download_path, target_folder_path, [pkg.full_path for pkg in contained_files])

        self._ctx.file_system.unlink(download_path)

        if len(job.filtered_data['files']) > 0:
            job.files_to_remove = [PathPackage(full_path=file_path, rel_path=file_path, drive=None, description=file_description) for file_path, file_description in job.filtered_data['files'].items()]

        if len(job.filtered_data['folders']) > 0:
            job.directories_to_remove = [PathPackage(full_path=folder_path, rel_path=folder_path, drive=None, description=folder_description) for folder_path, folder_description in job.filtered_data['folders'].items()]

        invalid_files: List[PathPackage] = []
        validated_files: List[PathPackage] = []
        for file_pkg in contained_files:
            if self._ctx.file_system.hash(file_pkg.full_path) == file_pkg.description['hash']:
                validated_files.append(file_pkg)
            else:
                invalid_files.append(file_pkg)

        job.downloaded_files.extend(validated_files)
        if len(invalid_files) > 0:
            self._ctx.installation_report.unmark_processed_files(invalid_files, job.db.db_id)
            return [ProcessIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=job.config,
                index=Index(files={file.rel_path: file.description for file in invalid_files}, folders={}),
                store=job.store.select(files=invalid_files),  # @TODO: This store needs to be a fragment only for the invalid files...
                full_resync=job.full_resync
            )], None
        else:
            return [], None

    def _process_create_folders_packages(self, db: DbEntity, create_folder_pkgs: List[PathPackage]) -> List[PathPackage]:
        # @TODO inspired in ProcessIndexWorker._process_create_folders_packages
        folders_to_create: Set[str] = set()
        for pkg in create_folder_pkgs:
            if pkg.is_pext_parent:
                continue

            if self._ctx.file_system.is_folder(pkg.full_path):
                continue

            if pkg.pext_props:
                folders_to_create.add(pkg.pext_props.parent_full_path())

            folders_to_create.add(pkg.full_path)
        for full_folder_path in sorted(folders_to_create, key=lambda x: len(x), reverse=True):
            self._ctx.file_system.make_dirs(full_folder_path)
        self._ctx.installation_report.add_processed_folders(create_folder_pkgs, db.db_id)
        return create_folder_pkgs

    def _extract_single_files(self, job: OpenZipContentsJob) -> WorkerResult:
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
            self._ctx.installation_report.add_processed_files(contained_files, job.db.db_id)

            for pkg in contained_files:
                file_path = pkg.rel_path
                file_description = pkg.description
                try:
                    self._ctx.file_system.copy(str(Path(tmp_path) / Path(file_description['zip_path'])), file_path)
                except FileCopyError as _e:
                    job.failed_files.append(pkg)
                    self._ctx.logger.print('ERROR: File "%s" could not be copied, skipping.' % file_path)
                    continue

                job.downloaded_files.append(pkg)

        self._ctx.file_system.unlink(download_path)
        self._ctx.file_system.remove_non_empty_folder(tmp_path)
        temp_filename.close()
        return [], None
