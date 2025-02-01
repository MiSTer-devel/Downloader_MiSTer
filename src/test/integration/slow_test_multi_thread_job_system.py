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

import time
import unittest
from functools import reduce
from typing import Dict, Optional
from downloader.job_system import JobSystem, ProgressReporter, Worker, Job, CycleDetectedException
from downloader.logger import NoLogger
from test.unit.test_single_thread_job_system import TestSingleThreadJobSystem, TestJob, TestWorker


class TestMultiThreadJobSystem(TestSingleThreadJobSystem):

    def test_base_provides_tests(self): self.assertGreater(len([m for m in dir(self) if m.startswith('test_')]), 5)
    def sut(self, reporter: ProgressReporter) -> JobSystem: return JobSystem(reporter, logger=NoLogger(), max_threads=20)

    def test_cancel_pending_jobs___when_there_are_many_jobs_produced___jobs_in_progress_will_fail_and_no_more_will_start(self):
        self.system = JobSystem(self.reporter, logger=NoLogger(), max_threads=3, max_cycle=100)
        self.system.register_worker(1, SlowWorker(self.system))
        self.system.push_job(TimedJob(iterations=1000))
        self.system.push_job(TimedJob(iterations=10))
        self.system.push_job(TimedJob(iterations=1000))
        self.system.execute_jobs()

        self.assertLess(30, self.reporter.completed_jobs[1])
        self.assertGreater(100, self.reporter.completed_jobs[1])
        self.assertGreater(4, self.reporter.cancelled_jobs[1] if self.reporter.cancelled_jobs else 0)
        self.assertFalse(self.system.timed_out())

    def test_timeout___when_job_takes_too_long___cancel_remaining_jobs_and_reports_timed_out(self):
        self.system = JobSystem(self.reporter, logger=NoLogger(), max_threads=3, max_cycle=10000, max_timeout=0.01)
        self.system.register_worker(1, SlowWorker(self.system))
        self.system.push_job(TimedJob(iterations=10000, wait=0.2))
        self.system.execute_jobs()

        self.assertReports(started={1: 1}, completed={1: 1}, timed_out=True)


    def assertReports(self, completed: Optional[Dict[int, int]] = None, started: Optional[Dict[int, int]] = None, in_progress: Optional[Dict[int, int]] = None, failed: Optional[Dict[int, int]] = None, retried: Optional[Dict[int, int]] = None, cancelled: Optional[Dict[int, int]] = None, pending: int = 0, timed_out: bool = False):
        expected = {
            'completed_jobs': completed or {},
            'started_jobs': started or completed or {},
            'in_progress_jobs': in_progress,
            'failed_jobs': failed or {},
            'retried_jobs': retried or {},
            'cancelled_jobs': cancelled or {},
            'pending_jobs_amount': pending,
            'timed_out': timed_out
        }
        actual = {
            'completed_jobs': self.reporter.completed_jobs,
            'started_jobs': self.reporter.started_jobs,
            'in_progress_jobs': self.reporter.in_progress_jobs,
            'failed_jobs': self.reporter.failed_jobs,
            'retried_jobs': self.reporter.retried_jobs,
            'cancelled_jobs': self.reporter.cancelled_jobs,
            'pending_jobs_amount': self.system.pending_jobs_amount(),
            'timed_out': self.system.timed_out()
        }
        if expected['in_progress_jobs'] is None:
            del expected['in_progress_jobs']
            del actual['in_progress_jobs']
        self.assertEqual(expected, actual)


class TimedJob(Job):
    @property
    def type_id(self): return 1
    def __init__(self, iterations: int, wait: float = 0, counter: int = 0):
        self.iterations = iterations
        self.wait = wait
        self.counter = counter

class SlowWorker(Worker):
    def __init__(self, system: JobSystem):
        self.system = system

    def operate_on(self, job: TimedJob):
        if job.wait > 0: time.sleep(job.wait)
        if job.counter > job.iterations:
            self.system.cancel_pending_jobs()
        return TimedJob(job.iterations, counter=job.counter + 1), None


if __name__ == '__main__':
    unittest.main()
