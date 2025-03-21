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

from typing import List, Optional

from downloader.job_system import ProgressReporter, Job, JobSystem as ProductionJobSystem, JobFailPolicy
from downloader.jobs.reporters import JobTagTracking
from test.fake_logger import NoLogger


class JobSystem(ProductionJobSystem):
    def __init__(self, fail_policy: Optional[JobFailPolicy] = None, progress_reporter: Optional[ProgressReporter] = None):
        super().__init__(
            logger=NoLogger(),
            max_threads=1,
            fail_policy=fail_policy or JobFailPolicy.FAIL_FAST,
            max_timeout=1,
            reporter=progress_reporter or TestProgressReporter()
        )


class ProgressReporterTracker(ProgressReporter):
    def __init__(self, reporter: ProgressReporter):
        self.tracks = {
            "job_started": [],
            "work_in_progress": 0,
            "job_completed": [],
            "job_cancelled": [],
            "job_failed": [],
            "job_retried": []
        }
        self._reporter = reporter

    def notify_job_started(self, job: Job) -> None:
        self.tracks["job_started"].append((job.__class__.__name__, str(job)))
        self._reporter.notify_job_started(job)

    def notify_work_in_progress(self) -> None:
        self.tracks["work_in_progress"] += 1
        self._reporter.notify_work_in_progress()

    def notify_jobs_cancelled(self, jobs: List[Job]) -> None:
        self.tracks["job_cancelled"].extend([(job.__class__.__name__, str(job)) for job in jobs])
        self._reporter.notify_jobs_cancelled(jobs)

    def notify_job_completed(self, job: Job, next_jobs: List[Job]) -> None:
        self.tracks["job_completed"].append((job.__class__.__name__, str(job)))
        self._reporter.notify_job_completed(job, next_jobs)

    def notify_job_failed(self, job: Job, exception: Exception) -> None:
        self.tracks["job_failed"].append((job.__class__.__name__, str(job), exception))
        self._reporter.notify_job_failed(job, exception)

    def notify_job_retried(self, job: Job, retry_job: Job, exception: Exception) -> None:
        self.tracks["job_retried"].append((job.__class__.__name__, str(job), exception))
        self._reporter.notify_job_retried(job, retry_job, exception)


class TestProgressReporter(ProgressReporter):

    def __init__(self):
        self.started_jobs = {}
        self.completed_jobs = {}
        self.failed_jobs = {}
        self.retried_jobs = {}
        self.cancelled_jobs = {}
        self.tracker = JobTagTracking()

    def reset(self): self.__init__()

    def notify_work_in_progress(self):
        pass

    def notify_jobs_cancelled(self, jobs: List[Job]) -> None:
        for job in jobs:
            job.add_tag(job.type_id)
            self.cancelled_jobs[job.type_id] = self.cancelled_jobs.get(job.type_id, 0) + 1
        self.tracker.add_jobs_cancelled(jobs)

    def notify_job_started(self, job: Job):
        job.add_tag(job.type_id)
        self.started_jobs[job.type_id] = self.started_jobs.get(job.type_id, 0) + 1
        self.tracker.add_job_started(job)

    def notify_job_completed(self, job: Job, next_jobs: List[Job]):
        job.add_tag(job.type_id)
        for c_job in next_jobs: c_job.add_tag(c_job.type_id)
        self.completed_jobs[job.type_id] = self.completed_jobs.get(job.type_id, 0) + 1
        self.tracker.add_job_completed(job, next_jobs)

    def notify_job_failed(self, job: Job, _exception: BaseException):
        job.add_tag(job.type_id)
        self.failed_jobs[job.type_id] = self.failed_jobs.get(job.type_id, 0) + 1
        self.tracker.add_job_failed(job)

    def notify_job_retried(self, job: Job, retry_job: Job, _exception: BaseException):
        job.add_tag(job.type_id)
        retry_job.add_tag(retry_job.type_id)
        self.retried_jobs[job.type_id] = self.retried_jobs.get(job.type_id, 0) + 1
        self.tracker.add_job_retried(job, retry_job)
