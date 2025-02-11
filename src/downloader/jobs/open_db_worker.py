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

from downloader.db_entity import DbEntity, DbEntityValidationException
from downloader.file_system import FsError
from downloader.job_system import WorkerResult
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.worker_context import DownloaderWorkerBase


class OpenDbWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return OpenDbJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenDbJob) -> WorkerResult:  # type: ignore[override]
        try:
            db = self._open_db(section=job.section, temp_path=job.temp_path)
        except Exception as e:
            self._ctx.logger.debug(e)
            return [], e

        ini_description, store, full_resync = job.ini_description, job.store, job.full_resync
        return [ProcessDbJob(db=db, ini_description=ini_description, store=store, full_resync=full_resync).add_tag(f'db:{job.section}')], None

    def _open_db(self, section: str, temp_path: str) -> DbEntity:
        db_raw = self._ctx.file_system.load_dict_from_file(temp_path)
        self._ctx.file_system.unlink(temp_path)
        self._ctx.logger.bench(f'Validating database {section}...')
        return DbEntity(db_raw, section)
