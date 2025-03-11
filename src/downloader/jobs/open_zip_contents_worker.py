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
from typing import Optional, Union

from downloader.job_system import WorkerResult
from downloader.jobs.process_db_index_worker import create_fetch_jobs
from downloader.path_package import PATH_PACKAGE_KIND_STANDARD, PATH_TYPE_FILE, PATH_TYPE_FOLDER, PathPackage
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.file_system import UnzipError


class OpenZipContentsWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return OpenZipContentsJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenZipContentsJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        logger.bench('OpenZipContentsWorker start: ', job.db.db_id, job.zip_id)

        zip_paths: Optional[dict[str, str]]
        if job.zip_kind == ZipKind.EXTRACT_ALL_CONTENTS:
            should_extract_all = len(job.files_to_unzip) > (0.7 * job.total_amount_of_files_in_zip)
            if should_extract_all:
                zip_paths = None
            else:
                root_zip_path = os.path.join(job.target_folder.rel_path, '')  # type: ignore[union-attr]
                zip_paths = {pkg.description.get('zip_path', None) or pkg.rel_path.removeprefix(root_zip_path): pkg.full_path for pkg in job.files_to_unzip}
        elif job.zip_kind == ZipKind.EXTRACT_SINGLE_FILES:
            should_extract_all = False
            zip_paths = {pkg.description['zip_path']: pkg.full_path for pkg in job.files_to_unzip}
        else: raise ValueError(f"Impossible kind '{job.zip_kind}' for zip '{job.zip_id}' in db '{job.db.db_id}'")

        target_path: Union[str, dict[str, str]] = job.target_folder.full_path if should_extract_all else (zip_paths or {})  # type: ignore[union-attr]
        self._ctx.file_download_session_logger.print_progress_line(job.action_text)
        logger.bench('OpenZipContentsWorker unzipping...', job.db.db_id, job.zip_id)
        try:
            self._ctx.file_system.unzip_contents(job.transfer_job.transfer(), target_path, (job.target_folder, job.files_to_unzip, job.filtered_data['files']))  # type: ignore[union-attr]
        except UnzipError as e:
            self._ctx.swallow_error(e)
            return [], e

        logger.bench('OpenZipContentsWorker unzip done...', job.db.db_id, job.zip_id)

        if should_extract_all:
            if len(job.filtered_data['files']) > 0:
                job.files_to_remove = [
                    PathPackage(file_path, None, file_description, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD, None) for file_path, file_description in job.filtered_data['files'].items()
                ]

            if len(job.filtered_data['folders']) > 0:
                job.directories_to_remove = [
                    PathPackage(folder_path, None, folder_description, PATH_TYPE_FOLDER, PATH_PACKAGE_KIND_STANDARD, None) for folder_path, folder_description in job.filtered_data['folders'].items()
                ]

        job.downloaded_files.extend(job.files_to_unzip)

        logger.bench('OpenZipContentsWorker precaching is_file...', job.db.db_id, job.zip_id)
        self._ctx.file_system.precache_is_file_with_folders(job.recipient_folders, recheck=True)

        logger.bench('OpenZipContentsWorker validating...', job.db.db_id, job.zip_id)

        existing_files, invalid_files = self._ctx.file_system.are_files(job.files_to_unzip)
        for file_pkg in existing_files:
            if self._ctx.file_system.hash(file_pkg.full_path) == file_pkg.description['hash']:
                job.validated_files.append(file_pkg)
            else:
                invalid_files.append(file_pkg)

        logger.bench('OpenZipContentsWorker validation done...', job.db.db_id, job.zip_id)

        if len(invalid_files) == 0:
            return [], None

        if job.zip_base_files_url == '':
            for file_pkg in invalid_files:
                if 'url' not in file_pkg.description:
                    job.failed_files.append(file_pkg)

        logger.bench('OpenZipContentsWorker launching recovery process index...', job.db.db_id, job.zip_id)

        return create_fetch_jobs(self._ctx, job.db.db_id, invalid_files, [], set(), job.zip_description.get('base_files_url', job.db.base_files_url)), None