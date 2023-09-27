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
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.worker_context import DownloaderWorker


class OpenDbWorker(DownloaderWorker):
    def initialize(self): self._ctx.job_system.register_worker(OpenDbJob.type_id, self)
    def reporter(self): return self._ctx.file_download_reporter

    def operate_on(self, job: OpenDbJob):
        section, temp_path, suffix = job.section, job.temp_path, job.suffix
        db = self._open_db(section, temp_path, suffix)
        ini_description, store, full_resync = job.ini_description, job.store, job.full_resync
        self._ctx.job_system.push_job(ProcessDbJob(db=db, ini_description=ini_description, store=store, full_resync=full_resync))

    def _open_db(self, section: str, temp_path: str, suffix: str) -> DbEntity:
        try:
            db_raw = self._ctx.file_system.load_dict_from_file(temp_path, suffix)
            self._ctx.file_system.unlink(temp_path)
            self._ctx.logger.bench(f'Validating database {section}...')
            return DbEntity(db_raw, section)
        except Exception as e:
            self._ctx.logger.debug(e)
            if isinstance(e, DbEntityValidationException):
                self._ctx.logger.print(str(e))
            self._ctx.logger.print(f'Could not load json from "{temp_path}"')
