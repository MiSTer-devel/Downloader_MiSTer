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

from downloader.constants import PathType
from downloader.db_entity import DbEntity
from downloader.file_filter import FileFilterFactory
from downloader.jobs.index import Index
from downloader.jobs.path_package import PathPackage
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.file_system import FileCopyError
from downloader.target_path_calculator import TargetPathsCalculator


class OpenZipContentsWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._files_that_failed_from_zip = []

    def initialize(self): self._ctx.job_system.register_worker(OpenZipContentsJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: OpenZipContentsJob):
        kind = job.zip_description.get('kind', None)
        if kind == 'extract_all_contents':
            self._extract_all_contents(
                db=job.db,
                config=job.config,
                zip_id=job.zip_id,
                zip_description=job.zip_description,
                download_path=job.download_path,
                index=job.index,
                files=job.files
            )
        elif kind == 'extract_single_files':
            self._extract_single_files(
                zip_id=job.zip_id,
                zip_description=job.zip_description,
                download_path=job.download_path,
                index=job.index
            )
        else:
            # @TODO: Handle this case
            raise Exception(f"Unknown kind '{kind}' for zip '{job.zip_id}' in db '{job.db.db_id}'")

    def _extract_all_contents(self, db: DbEntity, config: Dict[str, Any], zip_id: str, zip_description: Dict[str, Any], download_path: str, index: Index, files: List[PathPackage]):
        self._ctx.logger.print(zip_description['description'])

        target_folder_path = self._ctx.target_paths_calculator_factory\
            .target_paths_calculator(config)\
            .deduce_target_path(zip_description['target_folder_path'], {}, PathType.FOLDER)

        contained_files = [pkg.full_path for pkg in files]

        self._ctx.file_system.unzip_contents(download_path, target_folder_path, contained_files)
        self._ctx.file_system.unlink(download_path)

        # @TODO: This filtering looks like should be done in a previous step, but the removal of the files should be here. There should be a job.files_to_remove for that
        #        The filtering should be in a previous step because it should be accounted for when determining whether we need to download the contents file or not
        #        which currently happens in ProcessZipWorker.
        _, filtered_zip_data = FileFilterFactory(self._ctx.logger).create(db, config).select_filtered_files(index)

        filtered_files = filtered_zip_data[zip_id]['files'] if zip_id in filtered_zip_data else []
        for pkg in files:
            if pkg.rel_path in filtered_files:
                self._ctx.file_system.unlink(pkg.full_path)

    def _extract_single_files(self, zip_id: str, zip_description: Dict[str, Any], download_path: str, index: Index):
        self._ctx.logger.print(zip_description['description'])

        temp_filename = self._ctx.file_system.unique_temp_filename()
        tmp_path = '%s_%s/' % (temp_filename.value, zip_id)

        self._ctx.file_system.unzip_contents(download_path, tmp_path, list(index.files))

        for file_path, file_description in index.files.items():
            try:
                self._ctx.file_system.copy('%s%s' % (tmp_path, file_description['zip_path']), file_path)
            except FileCopyError as _e:
                self._files_that_failed_from_zip.append(file_path)
                self._ctx.logger.print('ERROR: File "%s" could not be copied, skipping.' % file_path)

        self._ctx.file_system.unlink(download_path)
        self._ctx.file_system.remove_non_empty_folder(tmp_path)
        temp_filename.close()
