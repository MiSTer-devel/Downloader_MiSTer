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

from downloader.job_system import WorkerResult, JobContext, ProgressReporter
from downloader.jobs.index import Index
from downloader.jobs.process_db_index_job import ProcessDbIndexJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.reporters import InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.wait_db_zips_job import WaitDbZipsJob
from downloader.logger import Logger


# Worker for waiting for the zip jobs to be done.
# This way decentralized orchestration happens only here, and the job can be removed once we make tag-based scheduling
# in the job system, so that we can centralize scheduling there.

class WaitDbZipsWorker(DownloaderWorker):
    def __init__(self, logger: Logger, installation_report: InstallationReportImpl, worker_context: JobContext, progress_reporter: ProgressReporter) -> None:
        self._logger = logger
        self._installation_report = installation_report
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter

    def job_type_id(self) -> int: return WaitDbZipsJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: WaitDbZipsJob) -> WorkerResult:  # type: ignore[override]
        self._logger.bench('WaitDbZipsWorker wait start: ', job.db.db_id)

        while self._installation_report.any_in_progress_job_with_tags(job.zip_job_tags):
            self._worker_context.wait_for_other_jobs(0.1)

        self._logger.bench('WaitDbZipsWorker wait done: ', job.db.db_id)
        index = Index(files=job.db.files, folders=job.db.folders)

        zip_indexes = []
        for tag in job.zip_job_tags:
            for zip_job in self._installation_report.get_jobs_completed_by_tag(tag):
                if isinstance(zip_job, ProcessZipIndexJob):
                    zip_indexes.append(zip_job.zip_index)
            for zip_job in self._installation_report.get_jobs_failed_by_tag(tag):
                if isinstance(zip_job, ProcessZipIndexJob):
                    if len(zip_job.full_partitions) > 0:
                        return [], None

        self._logger.bench('WaitDbZipsWorker deselect_all start: ', job.db.db_id)
        store = job.store.deselect_all(zip_indexes)
        self._logger.bench('WaitDbZipsWorker deselect_all done: ', job.db.db_id)

        resulting_job = ProcessDbIndexJob(
            db=job.db,
            ini_description=job.ini_description,
            config=job.config,
            index=index,
            store=store,
        )
        self._logger.bench('WaitDbZipsWorker done: ', job.db.db_id)
        return [resulting_job], None
