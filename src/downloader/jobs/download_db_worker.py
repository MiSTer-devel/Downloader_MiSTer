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

from pathlib import Path
from typing import Dict

from downloader.constants import K_DB_URL
from downloader.jobs.download_db_job import DownloadDbJob
from downloader.jobs.jobs_factory import make_get_file_job
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.worker_context import DownloaderWorker


class DownloadDbWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(DownloadDbJob.type_id, self)
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: DownloadDbJob):
        db_url, db_target = self._get_db_description_from_ini_section(job.ini_section, job.ini_description)
        get_file_job = make_get_file_job(source=db_url, target=db_target, info=job.ini_section, silent=True, logger=self._ctx.logger)
        get_file_job.after_job = OpenDbJob(
            temp_path=db_target,
            section=job.ini_section,
            ini_description=job.ini_description,
            store=job.store,
            full_resync=job.full_resync,
            get_file_job=get_file_job
        )
        self._ctx.job_system.push_job(get_file_job)

    def _get_db_description_from_ini_section(self, ini_section: str, ini_description: Dict[str, str]) -> tuple[str, str]:
        db_url = ini_description[K_DB_URL]
        db_target = str(Path(self._ctx.file_system.persistent_temp_dir()) / ini_section.replace('/', '_')) + Path(db_url).suffix.lower()
        return db_url, db_target
