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

from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.jobs.jobs_factory import make_process_zip_job


class OpenZipIndexWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(OpenZipIndexJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: OpenZipIndexJob):
        index = self._ctx.file_system.load_dict_from_file(job.download_path)
        self._ctx.file_system.unlink(job.download_path)

        self._ctx.job_system.push_job(make_process_zip_job(
            zip_id=job.zip_id,
            zip_description=job.zip_description,
            zip_index=index,
            config=job.config,
            db=job.db,
            ini_description=job.ini_description,
            store=job.store,
            full_resync=job.full_resync,
            has_new_zip_index=True
        ))
