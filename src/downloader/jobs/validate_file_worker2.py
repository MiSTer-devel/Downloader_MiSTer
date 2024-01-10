# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>
import os.path
from pathlib import Path
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

from typing import Optional
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadException


class ValidateFileWorker2(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(ValidateFileJob2.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: ValidateFileJob2):
        self._validate_file(
            temp_path=job.temp_path,
            target_file_path=job.target_file_path,
            info=job.info,
            file_hash=job.description['hash'],
            backup=job.description.get('backup', None)
        )

        if job.after_job is not None:
            self._ctx.job_system.push_job(job.after_job)

    def _validate_file(self, temp_path: str, target_file_path: str, info: str, file_hash: str, backup: Optional[str]):
        fs_hash = self._ctx.file_system.hash(temp_path)
        if fs_hash != file_hash:
            self._ctx.file_system.unlink(temp_path)
            raise FileDownloadException(f'Bad hash on {info} ({file_hash} != {fs_hash})')

        if temp_path != target_file_path:
            if backup is not None and self._ctx.file_system.is_file(target_file_path, use_cache=False):
                self._ctx.file_system.move(target_file_path, str(Path(target_file_path).parent / backup))
            self._ctx.file_system.move(temp_path, target_file_path)
