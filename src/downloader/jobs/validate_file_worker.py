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

from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.errors import FileDownloadError
from downloader.job_system import WorkerResult
from typing import Optional


class ValidateFileWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ValidateFileJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ValidateFileJob) -> WorkerResult:  # type: ignore[override]
        file_path, file_hash, hash_check = job.fetch_job.path, job.fetch_job.description['hash'], job.fetch_job.hash_check
        error = self._validate_file(file_path, file_hash, hash_check)
        if error is not None:
            return [], error

        return [] if job.fetch_job.after_validation is None else [job.fetch_job.after_validation], None

    def _validate_file(self, file_path: str, file_hash: str, hash_check: bool) -> Optional[Exception]:
        try:
            target_path = self._ctx.target_path_repository.access_target(file_path)
            if not self._ctx.file_system.is_file(target_path, use_cache=False):
                self._ctx.target_path_repository.clean_target(file_path)
                return FileDownloadError(f'Missing {file_path}')

            path_hash = self._ctx.file_system.hash(target_path)
            if hash_check and path_hash != file_hash:
                self._ctx.target_path_repository.clean_target(file_path)
                return FileDownloadError(f'Bad hash on {file_path} ({file_hash} != {path_hash})')

            self._ctx.target_path_repository.finish_target(file_path)
        except BaseException as e:
            return FileDownloadError(f'Exception during validation! {file_path}: {str(e)}')
        else: return None
