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

from typing import Optional
from downloader.job_system import Job, WorkerResult
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.index import Index
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.process_db_zips_waiter_job import ProcessDbZipsWaiterJob


# Worker for waiting for the zip jobs to be done.
# This way decentralized orchestration happens only here, and the job can be removed once we make tag-based scheduling
# in the job system, so that we can centralize scheduling there.

class ProcessDbZipsWaiterWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return ProcessDbZipsWaiterJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: ProcessDbZipsWaiterJob) -> WorkerResult:  # type: ignore[override]

        while self._ctx.installation_report.any_in_progress_job_with_tags(job.zip_job_tags):
            self._ctx.job_ctx.wait_for_other_jobs()

        index = Index(files=job.db.files, folders=job.db.folders, base_files_url=job.db.base_files_url)

        store = job.store
        for _tag, zip_jobs in self._ctx.installation_report.get_jobs_completed_by_tags(job.zip_job_tags):
            for zip_job in zip_jobs:
                if isinstance(zip_job, ProcessZipJob):
                    if zip_job.not_enough_space:
                        return [], None

                    store = job.store.deselect(zip_job.zip_index)

        resulting_job = ProcessIndexJob(
            db=job.db,
            ini_description=job.ini_description,
            config=job.config,
            index=index,
            store=store,
            full_resync=job.full_resync,
        )
        return [resulting_job], None
