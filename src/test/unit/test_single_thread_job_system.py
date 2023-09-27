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

import unittest
from functools import reduce

from downloader.job_system import Job, JobSystem, Worker, CycleDetectedException, ProgressReporter, NoWorkerException, CantRegisterWorkerException
import logging
from typing import Dict, Optional

from downloader.logger import NoLogger


class TestSingleThreadJobSystem(unittest.TestCase):

    def sut(self, reporter: ProgressReporter) -> JobSystem: return JobSystem(reporter, logger=NoLogger(), max_threads=1)

    def setUp(self):
        self.reporter = TestProgressReporter()
        self.system = self.sut(reporter=self.reporter)

    def test_accomplish_pending_jobs___reports_completed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))

        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))

        self.assertEqual(self.system.pending_jobs_amount(), 3)
        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 3})

    def test_accomplish_dynamic_jobs___reports_completed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.register_worker(3, TestWorker(self.system))
        self.system.register_worker(4, TestWorker(self.system))
        self.system.register_worker(5, TestWorker(self.system))

        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(2, next_job=TestJob(4)))
        self.system.push_job(TestJob(3, next_job=TestJob(5)))

        self.assertEqual(self.system.pending_jobs_amount(), 3)

        self.system.accomplish_pending_jobs()

        self.assertReports(completed={1: 1, 2: 1, 3: 1, 4: 1, 5: 1})

    def test_job_id_with_not_registered_worker___throws(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, next_job=TestJob(2)))

        with self.assertRaises(Exception) as context:
            self.system.accomplish_pending_jobs()

        self.assertIsInstance(context.exception, NoWorkerException)
        self.assertReports(started={1: 1}, in_progress={1: 1}, pending=1)

    def test_cycle_detection___throws(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))

        self.system.push_job(reduce(lambda acc, _: TestJob(1, next_job=TestJob(2, next_job=acc)), range(4), None))

        with self.assertRaises(Exception) as context:
            self.system.accomplish_pending_jobs()

        self.assertIsInstance(context.exception, CycleDetectedException)
        self.assertReports(completed={1: 3, 2: 3}, started={1: 3, 2: 3}, in_progress={}, pending=2)

    def test_cycle_detection___just_below_the_max_cycle_limit___doesnt_throw(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))

        self.system.push_job(reduce(lambda acc, _: TestJob(1, next_job=TestJob(2, next_job=acc)), range(3), None))

        self.system.accomplish_pending_jobs()

        self.assertReports(completed={1: 3, 2: 3}, started={1: 3, 2: 3}, in_progress={}, pending=0)

    def test_register_worker_during_accomplish_pending_jobs___throws(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, register_worker=TestWorker(self.system)))

        with self.assertRaises(Exception) as context:
            self.system.accomplish_pending_jobs()

        self.assertIsInstance(context.exception, CantRegisterWorkerException)
        self.assertReports(started={1: 1}, in_progress={1: 1}, pending=1)

    def test_retries___when_job_retries_itself___reports_completed_jobs_and_retries(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=3))
        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 1}, started={1: 4}, retried={1: 3})

    def test_failed___when_job_retries_itself___reports_failed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=4))
        self.system.accomplish_pending_jobs()
        self.assertReports(started={1: 4}, retried={1: 3}, failed={1: 1})

    def test_retries___when_job_retries_previous_job___reports_completed_jobs_and_retries(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.push_job(TestJob(1, next_job=TestJob(2, fails=1, retry_job=TestJob(1, next_job=TestJob(2)))))
        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 2, 2: 1}, started={1: 2, 2: 2}, retried={2: 1})

    def test_failed___when_job_retries_previous_job___reports_completed_jobs_and_failed_ones(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.push_job(TestJob(
            1, next_job=TestJob(2, fails=1, retry_job=TestJob(
                1, next_job=TestJob(2, fails=1, retry_job=TestJob(
                    1, next_job=TestJob(2, fails=1, retry_job=TestJob(
                        1, next_job=TestJob(2, fails=1, retry_job=TestJob(
                            1, next_job=TestJob(2)
                        ))
                    ))
                ))
            ))
        ))
        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 4}, started={1: 4, 2: 4}, retried={2: 3}, failed={2: 1})

    def test_cancel_pending_jobs___reports_completed_jobs_until_that_point_and_proper_pending_amount___then_resuming_works_as_expected(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.register_worker(3, TestWorker(self.system))
        self.system.register_worker(4, TestWorker(self.system))

        self.system.push_job(TestJob(1, next_job=(TestJob(2, cancel_pending_jobs=True, next_job=(TestJob(3, next_job=TestJob(4)))))))

        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 1, 2: 1, 3: 1}, pending=1)

        self.system.accomplish_pending_jobs()
        self.assertReports(completed={1: 1, 2: 1, 3: 1, 4: 1})

    def test_throwing_reporter_during_retries___does_not_incur_in_infinite_loop(self):
        class TestThrowingReporter(TestProgressReporter):
            def notify_job_retried(self, job: 'Job', exception: Exception):
                raise Exception('Houston, we have a problem.')

        reporter = TestThrowingReporter()
        system = self.sut(reporter=reporter)
        system.register_worker(1, TestWorker(system))
        system.push_job(TestJob(1, fails=3))

        logging.getLogger().setLevel(logging.CRITICAL + 1)
        system.accomplish_pending_jobs()
        logging.getLogger().setLevel(logging.NOTSET)

        self.assertEqual({1: 1}, reporter.completed_jobs)
        self.assertEqual({1: 4}, reporter.started_jobs)
        self.assertEqual({1: 3}, reporter.in_progress_jobs)
        self.assertEqual({}, reporter.retried_jobs)
        self.assertEqual({}, reporter.failed_jobs)
        self.assertEqual(0, system.pending_jobs_amount())

    def test_accomplish_pending_jobs_with_just_1_thread___reports_completed_jobs(self):
        reporter = TestProgressReporter()
        system = self.sut(reporter=reporter)
        system.register_worker(1, TestWorker(system))

        system.push_job(TestJob(1))
        system.push_job(TestJob(1))
        system.push_job(TestJob(1))

        self.assertEqual(system.pending_jobs_amount(), 3)
        system.accomplish_pending_jobs()

        self.assertEqual({1: 3}, reporter.completed_jobs)
        self.assertEqual({1: 3}, reporter.started_jobs)
        self.assertEqual({}, reporter.in_progress_jobs)
        self.assertEqual({}, reporter.retried_jobs)
        self.assertEqual({}, reporter.failed_jobs)
        self.assertEqual(0, system.pending_jobs_amount())

    def assertReports(self, completed: Optional[Dict[int, int]] = None, started: Optional[Dict[int, int]] = None, in_progress: Optional[Dict[int, int]] = None, failed: Optional[Dict[int, int]] = None, retried: Optional[Dict[int, int]] = None, pending: int = 0):
        self.assertEqual({
            'completed_jobs': len(completed or {}) > 0,
            'failed_jobs': failed or {},
            'retried_jobs': retried or {},
            'pending_jobs_amount': pending > 0
        }, {
            'completed_jobs': len(self.reporter.completed_jobs) > 0,
            'failed_jobs': self.reporter.failed_jobs,
            'retried_jobs': self.reporter.retried_jobs,
            'pending_jobs_amount': self.system.pending_jobs_amount() > 0
        })


class TestJob(Job):
    def __init__(self, type_id: int, next_job: Optional['TestJob'] = None, retry_job: Optional['TestJob'] = None, fails: int = 0, register_worker: Optional[Worker] = None,
                 cancel_pending_jobs: bool = False):
        self._type_id = type_id
        self._retry_job = retry_job
        self.next_job = next_job
        self.fails = fails
        self.register_worker = register_worker
        self.cancel_pending_jobs = cancel_pending_jobs

    @property
    def type_id(self) -> int:
        return self._type_id

    def retry_job(self):
        if self._retry_job is not None:
            return self._retry_job

        return super().retry_job()


class TestWorker(Worker):
    def __init__(self, system: JobSystem):
        self.system = system

    def operate_on(self, job: TestJob) -> None:
        if job.fails > 0:
            job.fails -= 1
            raise Exception('Fails!')

        if job.next_job is not None:
            self.system.push_job(job.next_job)

        if job.cancel_pending_jobs:
            self.system.cancel_pending_jobs()

        if job.register_worker is not None:
            self.system.register_worker(99, job.register_worker)


class TestProgressReporter(ProgressReporter):

    def __init__(self):
        self.started_jobs = {}
        self.in_progress_jobs = {}
        self.completed_jobs = {}
        self.failed_jobs = {}
        self.retried_jobs = {}

    def notify_work_in_progress(self):
        pass

    def notify_job_started(self, job: 'Job'):
        self.started_jobs[job.type_id] = self.started_jobs.get(job.type_id, 0) + 1
        self.in_progress_jobs[job.type_id] = self.in_progress_jobs.get(job.type_id, 0) + 1

    def notify_job_completed(self, job: 'Job'):
        self.completed_jobs[job.type_id] = self.completed_jobs.get(job.type_id, 0) + 1
        self._remove_in_progress(job)

    def notify_job_failed(self, job: 'Job', exception: BaseException):
        self.failed_jobs[job.type_id] = self.failed_jobs.get(job.type_id, 0) + 1
        self._remove_in_progress(job)

    def notify_job_retried(self, job: 'Job', exception: BaseException):
        self.retried_jobs[job.type_id] = self.retried_jobs.get(job.type_id, 0) + 1
        self._remove_in_progress(job)

    def _remove_in_progress(self, job: 'Job'):
        self.in_progress_jobs[job.type_id] = self.in_progress_jobs.get(job.type_id, 0) - 1
        if self.in_progress_jobs[job.type_id] <= 0:
            self.in_progress_jobs.pop(job.type_id)

