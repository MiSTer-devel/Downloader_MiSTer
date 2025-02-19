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

from dataclasses import fields, is_dataclass
from typing import Any, Dict, List
import copy

from downloader.job_system import ProgressReporter, Job


class ProgressReporterTracker(ProgressReporter):
    def __init__(self, reporter: ProgressReporter):
        self.tracks = {
            "job_started": [],
            "work_in_progress": 0,
            "job_completed": [],
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
        self.tracks["job_cancelled"] += 1
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


def cp(job: Any) -> Dict[str, Any]:
    if is_dataclass(job):
        return {
            field.name: copy.deepcopy(getattr(job, field.name))
            for field in fields(job)
        }

    if hasattr(job, '__dict__'):
        return copy.deepcopy(vars(job))

    slot_attrs = set()
    for cls in type(job).__mro__:
        if hasattr(cls, '__slots__'):
            slot_attrs.update(getattr(cls, '__slots__', ()))

    return {
        attr: copy.deepcopy(getattr(job, attr))
        for attr in slot_attrs
        if hasattr(job, attr)
    }
