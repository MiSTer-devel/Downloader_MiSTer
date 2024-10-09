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

from typing import List, Tuple, Optional

from downloader.file_filter import FileFilterFactory
from downloader.jobs.jobs_factory import make_get_zip_file_jobs, make_open_zip_contents_job
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.worker_context import DownloaderWorker, DownloaderWorkerContext
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.constants import K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.target_path_calculator import TargetPathsCalculator


class ProcessZipWorker(DownloaderWorker):
    def job_type_id(self) -> int: return ProcessZipJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessZipJob):
        total_files_size = 0
        for file_path, file_description in job.zip_index.files.items():
            total_files_size += file_description['size']

        needs_extracting_single_files = 'kind' in job.zip_description and job.zip_description['kind'] == 'extract_single_files'
        less_file_count = len(job.zip_index.files) < job.config[K_ZIP_FILE_COUNT_THRESHOLD]
        less_accumulated_mbs = total_files_size < (1000 * 1000 * job.config[K_ZIP_ACCUMULATED_MB_THRESHOLD])

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            self._ctx.job_ctx.push_job(ProcessIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=job.config,
                index=job.zip_index,
                store=job.store,
                full_resync=job.full_resync
            ))
        else:
            index, filtered_zip_data = FileFilterFactory(self._ctx.logger).create(job.db, job.zip_index, job.config).select_filtered_files(job.zip_index)

            file_packs: List[PathPackage] = []
            target_paths_calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)
            for file_path, file_description in index.files.items():
                file_packs.append(target_paths_calculator.deduce_target_path(file_path, file_description, PathType.FILE))

            self._ctx.logger.debug(f"Reserving space '{job.db.db_id}'...")
            if not self._try_reserve_space(file_packs):
                self._ctx.logger.debug(f"Not enough space '{job.db.db_id} zip:{job.zip_id}'!")
                for pkg in file_packs:
                    self._ctx.installation_report.add_failed_file(pkg.rel_path)
                return  # @TODO return error instead to retry later?

            folder_packs: List[PathPackage] = []
            for folder_path, folder_description in index.folders.items():
                folder_packs.append(target_paths_calculator.deduce_target_path(folder_path, folder_description, PathType.FOLDER))

            already_processed: Optional[Tuple[str, str]] = None
            with self._ctx.top_lock:
                for pkg in file_packs:
                    if self._ctx.installation_report.is_file_processed(pkg.rel_path):
                        already_processed = (pkg.rel_path, self._ctx.installation_report.processed_file(pkg.rel_path).db_id)
                        break
                    else:
                        self._ctx.installation_report.add_processed_file(pkg, job.db.db_id)

            if already_processed is not None:
                self._ctx.logger.print(f'Skipping zip "{job.zip_id}" because file "{already_processed[0]}" was already processed by db "{already_processed[1]}"')
                return

            get_file_job, info = make_open_zip_contents_job(
                job=job,
                zip_index=index,
                file_packs=file_packs,
                folder_packs=folder_packs,
                filtered_data=filtered_zip_data[job.zip_id] if job.zip_id in filtered_zip_data else {'files': {}, 'folders': {}}
            )
            self._ctx.job_ctx.push_job(get_file_job)

    def _try_reserve_space(self, file_packs: List[PathPackage]) -> bool:
        with self._ctx.top_lock:
            for pkg in file_packs:
                self._ctx.free_space_reservation.reserve_space_for_file(pkg.full_path,  pkg.description)

            self._ctx.logger.debug(f"Free space: {self._ctx.free_space_reservation.free_space()}")
            full_partitions = self._ctx.free_space_reservation.get_full_partitions()
            if len(full_partitions) > 0:
                for partition in full_partitions:
                    self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.partition_path} would get full!")

                #for pkg in fetch_pkgs:
                #    self._ctx.free_space_reservation.release_space_for_file(pkg.full_path, pkg.description)

                return False

        return True
