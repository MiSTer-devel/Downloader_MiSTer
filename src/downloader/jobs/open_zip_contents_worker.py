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

import os
from typing import List

from downloader.job_system import WorkerResult
from downloader.jobs.index import Index
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.path_package import PathPackage
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext, DownloaderWorkerFailPolicy
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.file_system import UnzipError


class OpenZipContentsWorker(DownloaderWorkerBase):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)

    def job_type_id(self) -> int: return OpenZipContentsJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenZipContentsJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        logger.bench('OpenZipContentsWorker start.')

        if job.zip_kind == ZipKind.EXTRACT_ALL_CONTENTS:
            should_extract_all = len(job.files_to_unzip) > (0.7 * job.total_amount_of_files_in_zip)
            if should_extract_all:
                zip_paths = None
            else:
                root_zip_path = os.path.join(job.target_folder.rel_path, '')
                zip_paths = {pkg.description.get('zip_path', None) or pkg.rel_path.removeprefix(root_zip_path): pkg.full_path for pkg in job.files_to_unzip}
        elif job.zip_kind == ZipKind.EXTRACT_SINGLE_FILES:
            should_extract_all = False
            zip_paths = {pkg.description['zip_path']: pkg.full_path for pkg in job.files_to_unzip}
        else: raise ValueError(f"Impossible kind '{job.zip_kind}' for zip '{job.zip_id}' in db '{job.db.db_id}'")

        target_path = job.target_folder.full_path if should_extract_all else zip_paths
        logger.print(job.action_text)
        logger.bench('OpenZipContentsWorker unzipping...')
        try:
            self._ctx.file_system.unzip_contents(job.contents_zip_temp_path, target_path, (job.target_folder, job.files_to_unzip, job.filtered_data['files']))
        except UnzipError as e:
            if self._ctx.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
                raise e
            return [], e
        finally:
            self._ctx.file_system.unlink(job.contents_zip_temp_path)

        logger.bench('OpenZipContentsWorker unzip done...')

        if should_extract_all:
            if len(job.filtered_data['files']) > 0:
                job.files_to_remove = [PathPackage(full_path=file_path, rel_path=file_path, drive=None, description=file_description) for file_path, file_description in job.filtered_data['files'].items()]

            if len(job.filtered_data['folders']) > 0:
                job.directories_to_remove = [PathPackage(full_path=folder_path, rel_path=folder_path, drive=None, description=folder_description) for folder_path, folder_description in job.filtered_data['folders'].items()]

        job.downloaded_files.extend(job.files_to_unzip)

        logger.bench('OpenZipContentsWorker validating...')

        invalid_files: List[PathPackage] = []
        for file_pkg in job.files_to_unzip:
            if self._ctx.file_system.is_file(file_pkg.full_path, use_cache=False) and self._ctx.file_system.hash(file_pkg.full_path) == file_pkg.description['hash']:
                job.validated_files.append(file_pkg)
            else:
                invalid_files.append(file_pkg)

        logger.bench('OpenZipContentsWorker validation done...')

        if len(invalid_files) == 0:
            return [], None

        if job.zip_base_files_url == '':
            files_to_recover = {}
            for file_pkg in invalid_files:
                if 'url' not in file_pkg.description:
                    job.failed_files.append(file_pkg)
                else:
                    files_to_recover[file_pkg.rel_path] = file_pkg.description
        else:
            files_to_recover = {file.rel_path: file.description for file in invalid_files}

        self._ctx.installation_report.unmark_processed_files(job.failed_files, job.db.db_id)

        logger.bench('OpenZipContentsWorker launching recovery process index...')

        return [ProcessIndexJob(
            db=job.db,
            ini_description=job.ini_description,
            config=job.config,
            index=Index(files=files_to_recover, folders={}),
            store=job.store.select(files=[pkg.rel_path for pkg in invalid_files]),  # @TODO: This store needs to be a fragment only for the invalid files...
            full_resync=job.full_resync
        )], None
