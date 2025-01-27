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

from typing import List, Tuple, Optional, Dict, Any

from downloader.file_filter import FileFilterFactory
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_get_zip_file_jobs, make_open_zip_contents_job
from downloader.local_store_wrapper import StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerContext
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.constants import K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.target_path_calculator import TargetPathsCalculator
from downloader.jobs.index import Index


class ProcessZipWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessZipJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessZipJob) -> WorkerResult:
        total_files_size = 0
        for file_path, file_description in job.zip_index.files.items():
            total_files_size += file_description['size']

        needs_extracting_single_files = 'kind' in job.zip_description and job.zip_description['kind'] == 'extract_single_files'
        less_file_count = len(job.zip_index.files) < job.config[K_ZIP_FILE_COUNT_THRESHOLD]
        less_accumulated_mbs = total_files_size < (1000 * 1000 * job.config[K_ZIP_ACCUMULATED_MB_THRESHOLD])

        next_job: Job

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            next_job = ProcessIndexJob(
                db=job.db,
                ini_description=job.ini_description,
                config=job.config,
                index=job.zip_index,
                store=job.store,
                full_resync=job.full_resync
            )
        else:
            zip_index, filtered_zip_data = FileFilterFactory(self._ctx.logger).create(job.db, job.zip_index, job.config).select_filtered_files(job.zip_index)

            file_packs: List[PathPackage] = []
            target_paths_calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)
            for file_path, file_description in zip_index.files.items():
                file_packs.append(target_paths_calculator.deduce_target_path(file_path, file_description, PathType.FILE))

            self._ctx.logger.debug(f"Reserving space '{job.db.db_id}'...")
            if not self._try_reserve_space(file_packs):
                self._ctx.logger.debug(f"Not enough space '{job.db.db_id} zip:{job.zip_id}'!")
                with self._ctx.top_lock:
                    for pkg in file_packs:
                        self._ctx.installation_report.add_failed_file(pkg.rel_path)
                job.not_enough_space = True
                next_job = None  # @TODO return error instead to retry later?
            else:
                folder_packs: List[PathPackage] = []
                for folder_path, folder_description in zip_index.folders.items():
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
                    return None, None

                get_file_job, info = make_open_zip_contents_job(
                    job=job,
                    zip_index=zip_index,
                    file_packs=file_packs,
                    folder_packs=folder_packs,
                    filtered_data=filtered_zip_data[job.zip_id] if job.zip_id in filtered_zip_data else {'files': {}, 'folders': {}}
                )
                next_job = get_file_job

        self._fill_fragment_with_zip_index(job.result_zip_index, job)
        return next_job, None

    def _try_reserve_space(self, file_packs: List[PathPackage]) -> bool:
        fits_well, full_partitions = self._ctx.free_space_reservation.reserve_space_for_file_pkgs(file_packs)
        if fits_well:
            return True
        else:
            for partition, _ in full_partitions:
                self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")
            with self._ctx.top_lock:
                # @TODO Should use a report lock instead of the top lock
                for partition, failed_reserve in full_partitions:
                    # @TODO Should add a collection instead of a single file to minimize lock time
                    self._ctx.installation_report.add_full_partition(partition, failed_reserve)

            return False

    def _fill_fragment_with_zip_index(self, fragment: StoreFragmentDrivePaths, job: ProcessZipJob):
        path = None
        if 'target_folder_path' in job.zip_description:
            path = job.zip_description['target_folder_path']
        elif 'path' in job.zip_description:
            path = job.zip_description['path']
        elif 'internal_summary' in job.zip_description:
            for file_path in job.zip_description['internal_summary']['files']:
                path = file_path
                break
            for folder_path in job.zip_description['internal_summary']['folders']:
                path = folder_path
                break
        else:
            for file_path in job.zip_index.files:
                path = file_path
                break

            for folder_path in job.zip_index.folders:
                path = folder_path
                break

        if path is None:
            return

        path_pkg = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)\
            .deduce_target_path(path, {}, PathType.FOLDER)

        if path_pkg.pext_props and path_pkg.is_pext_external:
            drive = path_pkg.pext_props.drive
            fragment['external_paths'][drive] = {'files': {}, 'folders': {}}
            for file_path, file_description in job.zip_index.files.items():
                fragment['external_paths'][drive]['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['external_paths'][drive]['folders'][folder_path[1:]] = folder_description
        elif path_pkg.is_pext_standard:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path[1:]] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path[1:]] = folder_description

        else:
            for file_path, file_description in job.zip_index.files.items():
                fragment['base_paths']['files'][file_path] = file_description

            for folder_path, folder_description in job.zip_index.folders.items():
                fragment['base_paths']['folders'][folder_path] = folder_description
