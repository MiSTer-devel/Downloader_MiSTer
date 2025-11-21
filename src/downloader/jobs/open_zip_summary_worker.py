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

from downloader.db_entity import check_zip_summary, ZipIndexEntity, fix_zip
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.open_zip_summary_job import OpenZipSummaryJob
from downloader.jobs.jobs_factory import make_process_zip_index_job
from downloader.job_system import WorkerResult

class OpenZipSummaryWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return OpenZipSummaryJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: OpenZipSummaryJob) -> WorkerResult:  # type: ignore[override]
        try:
            logger = self._ctx.logger
            db, zip_id = job.db, job.zip_id

            logger.bench('OpenZipSummaryWorker load dict: ', db.db_id, zip_id)
            summary = self._ctx.file_system.load_dict_from_transfer(job.transfer_job.source, job.transfer_job.transfer())  # type: ignore[union-attr]
            check_zip_summary(summary, db.db_id, zip_id)
            base_files_url = db.base_files_url
            if 'base_files_url' in job.zip_description:
                base_files_url = job.zip_description['base_files_url']

            zip_index = ZipIndexEntity(files=summary['files'],
                                       folders=summary['folders'],
                                       base_files_url=summary.get('base_files_url', base_files_url),
                                       version=summary.get('v', 0))

            if zip_index.needs_migration():
                logger.bench('OpenZipSummaryWorker migrating zip index entity: ', db.db_id, zip_id)
                error = zip_index.migrate(db.db_id)
                if error is not None:
                    self._ctx.swallow_error(error)
                    return [], error

            logger.bench('OpenZipSummaryWorker fix zips: ', db.db_id, zip_id)
            fix_zip(job.zip_description, zip_index)
            logger.bench('OpenZipSummaryWorker done: ', db.db_id, zip_id)

            return [make_process_zip_index_job(
                zip_id=zip_id,
                zip_description=job.zip_description,
                zip_index=zip_index,
                config=job.config,
                db=db,
                ini_description=job.ini_description,
                store=job.store,
                has_new_zip_summary=True
            )], None
        except Exception as e:
            self._ctx.swallow_error(e)
            return [], e
