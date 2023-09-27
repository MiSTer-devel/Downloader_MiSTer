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

from typing import Dict, Any
from pathlib import Path
import os

from downloader.constants import K_DB_URL
from downloader.job_system import Job
from downloader.jobs.download_db_job import DownloadDbJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.worker_context import DownloaderWorker
from downloader.local_store_wrapper import StoreWrapper


class DownloadDbWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(DownloadDbJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: DownloadDbJob):
        section, description, store, full_resync = job.ini_section, job.ini_description, job.store, job.full_resync
        result_job = self._download_db(section, description, store, full_resync)
        self._ctx.job_system.push_job(result_job)

    def _download_db(self, section: str, description: Dict[str, Any], store: StoreWrapper, full_resync: bool) -> Job:
        db_url = description[K_DB_URL]
        db_suffix = Path(db_url).suffix.lower()
        db_target = os.path.join(self._ctx.file_system.persistent_temp_dir(), section.replace('/', '_'))
        open_job = OpenDbJob(temp_path=db_target, suffix=db_suffix, section=section, ini_description=description, store=store, full_resync=full_resync, fetch_db=None)

        if not db_url.startswith("http"):
            if not db_url.startswith("/"):
                db_url = self._ctx.file_system.resolve(db_url)

            self._ctx.logger.debug(f'Loading db from local path: {db_url}')
            self._ctx.file_system.copy(db_url, db_target)
            return open_job
        else:
            self._ctx.logger.debug(f'Loading db from url: {db_url}')
            fetch_db = FetchFileJob2(download_path=db_target, info=section, url=db_url, silent=True)
            fetch_db.after_job = open_job
            open_job.fetch_db = fetch_db
            return fetch_db
