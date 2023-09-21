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
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadException


class ValidateFileWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(ValidateFileJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ValidateFileJob):
        file_path, file_hash, hash_check = job.fetch_job.path, job.fetch_job.description['hash'], job.fetch_job.hash_check
        self._validate_file(file_path, file_hash, hash_check)
        if job.fetch_job.after_validation is not None:
            self._ctx.job_system.push_job(job.fetch_job.after_validation)

    def _validate_file(self, file_path: str, file_hash: str, hash_check: bool):
        target_path = self._ctx.target_path_repository.access_target(file_path)
        if not self._ctx.file_system.is_file(target_path, use_cache=False):
            self._ctx.target_path_repository.clean_target(file_path)
            raise FileDownloadException(f'Missing {file_path}')

        path_hash = self._ctx.file_system.hash(target_path)
        if hash_check and path_hash != file_hash:
            self._ctx.target_path_repository.clean_target(file_path)
            raise FileDownloadException(f'Bad hash on {file_path} ({file_hash} != {path_hash})')

        self._ctx.target_path_repository.finish_target(file_path)
