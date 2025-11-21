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

from downloader.job_system import WorkerResult
from downloader.jobs.load_local_store_job import LoadLocalStoreJob
from downloader.jobs.worker_context import DownloaderWorkerBase


class LoadLocalStoreWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return LoadLocalStoreJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: LoadLocalStoreJob) -> WorkerResult:  # type: ignore[override]
        logger = self._ctx.logger
        logger.bench('LoadLocalStoreWorker start.')
        try:
            local_store = self._ctx.local_repository.load_store()

            logger.bench('LoadLocalStoreWorker relocating base paths')
            # @TODO: Remove this 1-2 years after the 2.0 release, which deprecated date base scoped base_paths
            for relocation_package in self._ctx.base_path_relocator.relocating_base_paths(job.db_pkgs, local_store):
                self._ctx.base_path_relocator.relocate_non_system_files(relocation_package)
                err = self._ctx.local_repository.save_store(local_store)
                if err is not None:
                    logger.debug('WARNING! Base path relocation could not be saved in the store!')
                    continue
        except Exception as e:
            self._ctx.swallow_error(e)
            return [], e

        job.local_store = local_store
        logger.bench('LoadLocalStoreWorker done.')
        return [], None
