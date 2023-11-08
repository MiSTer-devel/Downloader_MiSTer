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

from threading import Lock
from typing import List, Tuple, Optional

from downloader.jobs.jobs_factory import make_get_zip_file_jobs
from downloader.jobs.path_package import PathPackage
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.constants import K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD, PathType
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.target_path_calculator import TargetPathsCalculator


class ProcessZipWorker(DownloaderWorker):
    def __init__(self, ctx: DownloaderWorkerContext):
        super().__init__(ctx)
        self._lock = Lock()

    def initialize(self): self._ctx.job_system.register_worker(ProcessZipJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ProcessZipJob):
        total_files_size = 0
        for file_path, file_description in job.zip_index.files.items():
            total_files_size += file_description['size']

        needs_extracting_single_files = 'kind' in job.zip_description and job.zip_description['kind'] == 'extract_single_files'
        less_file_count = len(job.zip_index.files) < job.config[K_ZIP_FILE_COUNT_THRESHOLD]
        less_accumulated_mbs = total_files_size < (1000 * 1000 * job.config[K_ZIP_ACCUMULATED_MB_THRESHOLD])

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            self._ctx.job_system.push_job(ProcessIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=job.config,
                index=job.zip_index,
                store=job.store,
                full_resync=job.full_resync
            ))
        else:
            file_packs: List[PathPackage] = []
            deduce_target_path_calculator = TargetPathsCalculator.create_target_paths_calculator(self._ctx.file_system, job.config, self._ctx.external_drives_repository)
            for file_path, file_description in job.zip_index.files.items():
                target_file_path = deduce_target_path_calculator.deduce_target_path(file_path, file_description, PathType.FILE)
                file_packs.append(PathPackage(full_path=target_file_path, rel_path=file_path, description=file_description))

            already_processed: Optional[Tuple[str, str]] = None
            with self._lock:
                for pkg in file_packs:
                    if self._ctx.installation_report.is_file_processed(pkg.rel_path):
                        already_processed = (pkg.rel_path, self._ctx.installation_report.processed_file(pkg.rel_path).db_id)
                        break
                    else:
                        self._ctx.installation_report.add_processed_file(pkg.full_path, pkg.rel_path, pkg.description, job.db.db_id)

            if already_processed is not None:
                self._ctx.logger.print(f'Skipping zip "{job.zip_id}" because file "{already_processed[0]}" was already processed by db "{already_processed[1]}"')
                return

            get_file_job, validate_job = make_get_zip_file_jobs(db=job.db, zip_id=job.zip_id, description=job.zip_description['contents_file'])
            validate_job.after_job = OpenZipContentsJob(
                zip_id=job.zip_id,
                zip_description=job.zip_description,
                db=job.db,
                ini_description=job.ini_description,
                store=job.store,
                full_resync=job.full_resync,
                download_path=validate_job.target_file_path,
                files=file_packs,
                config=job.config,
                index=job.zip_index,
                get_file_job=get_file_job
            )
            self._ctx.job_system.push_job(get_file_job)
