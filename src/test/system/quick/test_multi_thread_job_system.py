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

import time
import unittest
from downloader.job_system import CantWaitWhenTimedOut, JobFailPolicy, JobSystem, JobSystemAbortException, Worker, Job
from test.fake_logger import NoLogger
from test.unit.test_single_thread_job_system import TestSingleThreadJobSystem


class TestMultiThreadJobSystem(TestSingleThreadJobSystem):

    def test_base_provides_tests(self): self.assertGreater(len([m for m in dir(self) if m.startswith('test_')]), 5)
    def sut(self, fail: JobFailPolicy = JobFailPolicy.FAIL_GRACEFULLY, activity_tracker=None, time_monotonic=None, threads: int = 20, max_cycle: int = 3, timeout: int = 0.5)  -> JobSystem:
        return JobSystem(self.reporter, logger=NoLogger(), max_threads=threads, activity_tracker=activity_tracker, time_monotonic=time_monotonic or time.monotonic, fail_policy=fail, max_cycle=max_cycle, wait_time=0.016, max_timeout=timeout)

    def test_cancel_pending_jobs___when_there_are_many_jobs_produced___jobs_in_progress_will_fail_and_no_more_will_start(self):
        self.system = self.sut(threads=3, max_cycle=100)
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
        self.system = self.sut(threads=3, max_cycle=10000, timeout=0)
        self.system.register_worker(1, SlowWorker(self.system))
        self.system.push_job(TimedJob(iterations=10000, wait=0.02))
        self.system.execute_jobs()

        self.assertReports(started={1: 1}, completed={1: 1}, timed_out=True)

    def test_wait_for_jobs___when_system_has_timed_out___throws(self):
        self.system = self.sut(threads=3, timeout=0)
        self.system.register_worker(1, SlowWorker(self.system))
        self.system.push_job(TimedJob(1, wait=0.25, wait_for_other_jobs=True))

        with self.assertRaises(Exception) as context:
            self.system.execute_jobs()

        self.assertIsInstance(context.exception, JobSystemAbortException)
        self.assertIsInstance(context.exception, CantWaitWhenTimedOut)

class TimedJob(Job):
    @property
    def type_id(self): return 1
    def __init__(self, iterations: int, wait: float = 0, counter: int = 0, wait_for_other_jobs: bool = False):
        self.iterations = iterations
        self.wait = wait
        self.counter = counter
        self.wait_for_other_jobs = wait_for_other_jobs

class SlowWorker(Worker):
    def __init__(self, system: JobSystem):
        self.system = system

    def operate_on(self, job: TimedJob):
        if job.wait > 0: time.sleep(job.wait)
        if job.wait_for_other_jobs: self.system.wait_for_other_jobs(0.001)
        if job.counter > job.iterations:
            self.system.cancel_pending_jobs()
        return [TimedJob(job.iterations, counter=job.counter + 1)], None


if __name__ == '__main__':
    unittest.main()
