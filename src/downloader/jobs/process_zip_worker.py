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

from typing import List, Optional, Tuple

from downloader.file_filter import FileFilterFactory
from downloader.free_space_reservation import Partition
from downloader.job_system import WorkerResult, Job
from downloader.jobs.jobs_factory import make_open_zip_contents_job
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.local_store_wrapper import StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.worker_context import DownloaderWorkerBase, DownloaderWorkerFailPolicy


class ProcessZipWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessZipJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessZipJob) -> WorkerResult:  # type: ignore[override]
        total_files_size = 0
        for file_path, file_description in job.zip_index.files.items():
            total_files_size += file_description['size']

        needs_extracting_single_files = 'kind' in job.zip_description and job.zip_description['kind'] == 'extract_single_files'
        less_file_count = len(job.zip_index.files) < job.config['zip_file_count_threshold']
        less_accumulated_mbs = total_files_size < (1000 * 1000 * job.config['zip_accumulated_mb_threshold'])

        if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
            job.skip_unzip = True
            next_jobs: List[Job] = [_make_process_index_job(job)]
        else:
            zip_index, filtered_zip_data = FileFilterFactory(self._ctx.logger).create(job.db, job.zip_index, job.config).select_filtered_files(job.zip_index)

            file_packs: List[PathPackage] = []
            target_paths_calculator = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)
            for file_path, file_description in zip_index.files.items():
                file_pkg, file_error = target_paths_calculator.deduce_target_path(file_path, file_description, PathType.FILE)
                if file_error is not None:
                     if self._ctx.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
                         raise file_error

                     self._ctx.logger.print(f'Error: {file_error}')

                file_packs.append(file_pkg)

            self._ctx.logger.debug(f"Reserving space '{job.db.db_id}'...")
            job.full_partitions = self._try_reserve_space(file_packs)
            if len(job.full_partitions) > 0:
                self._ctx.logger.debug(f"Not enough space '{job.db.db_id} zip:{job.zip_id}'!")
                job.failed_files_no_space = file_packs
                job.not_enough_space = True # @TODO return error instead to retry later?
                next_jobs = []
            else:
                folder_packs: List[PathPackage] = []
                for folder_path, folder_description in zip_index.folders.items():
                    folder_pkg, folder_error = target_paths_calculator.deduce_target_path(folder_path, folder_description, PathType.FOLDER)
                    if folder_error is not None:
                        if self._ctx.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
                            raise folder_error

                        self._ctx.logger.print(f'Error: {folder_error}')
                    folder_packs.append(folder_pkg)

                already_processed = self._ctx.installation_report.any_file_processed(file_packs)
                if already_processed is not None:
                    self._ctx.logger.print(f'Skipping zip "{job.zip_id}" because file "{already_processed.pkg.rel_path}" was already processed by db "{already_processed.db_id}"')
                    return [], None

                get_file_job, _ = make_open_zip_contents_job(
                    job=job,
                    zip_index=zip_index,
                    file_packs=file_packs,
                    folder_packs=folder_packs,
                    filtered_data=filtered_zip_data[job.zip_id] if job.zip_id in filtered_zip_data else {'files': {}, 'folders': {}},
                    make_process_index_backup=lambda: _make_process_index_job(job)
                )
                next_jobs: List[Job] = [get_file_job]

        self._fill_fragment_with_zip_index(job.result_zip_index, job)
        return next_jobs, None

    def _try_reserve_space(self, file_packs: List[PathPackage]) -> List[Tuple[Partition, int]]:
        fits_well, full_partitions = self._ctx.free_space_reservation.reserve_space_for_file_pkgs(file_packs)
        if fits_well:
            return []
        else:
            for partition, _ in full_partitions:
                self._ctx.file_download_session_logger.print_progress_line(f"Partition {partition.path} would get full!")

            return full_partitions

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

        path_pkg, path_error = self._ctx.target_paths_calculator_factory.target_paths_calculator(job.config)\
            .deduce_target_path(path, {}, PathType.FOLDER)

        if path_error is not None:
            if self._ctx.fail_policy == DownloaderWorkerFailPolicy.FAIL_FAST:
                raise path_error

            self._ctx.logger.print(f"ERROR: {path_error}")

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


def _make_process_index_job(job: ProcessZipJob) -> ProcessIndexJob:
    return ProcessIndexJob(
            db=job.db,
            ini_description=job.ini_description,
            config=job.config,
            index=job.zip_index,
            store=job.store.select(files=list(job.zip_index.files), folders=list(job.zip_index.folders)),
            full_resync=job.full_resync,
        )