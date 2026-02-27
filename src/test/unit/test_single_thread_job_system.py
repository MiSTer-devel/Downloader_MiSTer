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

import signal
import time
import unittest
from functools import reduce

from downloader.job_system import ActivityTracker, CantSetSignalsException, Job, JobFailPolicy, JobSystem, JobSystemAbortException, Worker, CycleDetectedException, \
    CantPushJobs, \
    CantRegisterWorkerException, CantExecuteJobs, CantWaitWhenNotExecutingJobs, WorkerResult
from typing import Callable, Dict, Optional, List

from test.fake_job_system import TestProgressReporter
from test.fake_logger import NoLogger


class TestSingleThreadJobSystem(unittest.TestCase):

    def sut(self, fail: JobFailPolicy = JobFailPolicy.FAIL_GRACEFULLY, activity_tracker: Optional[ActivityTracker] = None, time_monotonic: Optional[Callable] = None, timeout: float = 300) -> JobSystem:
        return JobSystem(self.reporter, logger=NoLogger(), max_threads=1, activity_tracker=activity_tracker, time_monotonic=time_monotonic or time.monotonic, fail_policy=fail, max_timeout=timeout)

    def setUp(self):
        self.reporter = TestProgressReporter()
        self.system = self.sut()

    def test_execute_jobs___reports_completed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))

        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))

        self.assertEqual(self.system.pending_jobs_amount(), 3)
        self.system.execute_jobs()
        self.assertReports(completed={1: 3})

    def test_execute_dynamic_jobs___reports_completed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.register_worker(3, TestWorker(self.system))
        self.system.register_worker(4, TestWorker(self.system))
        self.system.register_worker(5, TestWorker(self.system))

        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(2, next_job=TestJob(4)))
        self.system.push_job(TestJob(3, next_job=TestJob(5)))

        self.assertEqual(self.system.pending_jobs_amount(), 3)

        self.system.execute_jobs()

        self.assertReports(completed={1: 1, 2: 1, 3: 1, 4: 1, 5: 1})

    def test_wait_for_other_jobs___when_execute_jobs_is_not_called___throws(self):
        with self.assertRaises(Exception) as context:
            self.system.wait_for_other_jobs(0.001)

        self.assertIsInstance(context.exception, JobSystemAbortException)
        self.assertIsInstance(context.exception, CantWaitWhenNotExecutingJobs)

    def test_system_abortions___when_breaking_api_within_workers___throws(self):
        for spec, job, ex, result in [
            ('job_id_with_not_registered_worker', TestJob(1, next_job=TestJob(2)), CantPushJobs, {"completed": {1: 1}}),
            ('register_worker_during_execute_jobs', TestJob(1, register_worker=TestWorker(self.system)), CantRegisterWorkerException, {"failed": {1: 1}}),
            ('set_signals_during_execute_jobs', TestJob(1, set_signals=[]), CantSetSignalsException, {"failed": {1: 1}}),
            ('execute_jobs_within_worker', TestJob(1, execute_jobs=True), CantExecuteJobs, {"failed": {1: 1}}),
        ]:
            self.setUp()
            with self.subTest(spec):
                self.system.register_worker(1, TestWorker(self.system))
                self.system.push_job(job)

                with self.assertRaises(Exception) as context:
                    self.system.execute_jobs()

                self.assertIsInstance(context.exception, JobSystemAbortException)
                self.assertIsInstance(context.exception, ex)
                self.assertReports(started={1: 1}, errors=1, **result)

    def test_cycle_detection___throws(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))

        self.system.push_job(reduce(lambda acc, _: TestJob(1, next_job=TestJob(2, next_job=acc)), range(4), None))

        with self.assertRaises(Exception) as context:
            self.system.execute_jobs()

        self.assertIsInstance(context.exception, JobSystemAbortException)
        self.assertIsInstance(context.exception, CycleDetectedException)
        self.assertReports(completed={1: 4, 2: 3}, failed={2: 1}, errors=1)

    def test_cycle_detection___just_below_the_max_cycle_limit___doesnt_throw(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))

        self.system.push_job(reduce(lambda acc, _: TestJob(1, next_job=TestJob(2, next_job=acc)), range(3), None))

        self.system.execute_jobs()

        self.assertReports(completed={1: 3, 2: 3}, started={1: 3, 2: 3}, in_progress={}, pending=0)

    def test_cycle_detection___with_infinite_self_recursion___throws(self):
        self.system.register_worker(1, TestWorker(self.system))

        job = TestJob(1)
        job.next_job = job

        self.system.push_job(job)

        with self.assertRaises(Exception) as context:
            self.system.execute_jobs()

        self.assertIsInstance(context.exception, JobSystemAbortException)
        self.assertIsInstance(context.exception, CycleDetectedException)
        self.assertReports(completed={1: 4}, failed={1: 1}, errors=1)

    def test_retries___when_job_retries_itself___reports_completed_jobs_and_retries(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=3))
        self.system.execute_jobs()
        self.assertReports(completed={1: 1}, started={1: 4}, retried={1: 3})

    def test_failed___when_job_retries_itself___reports_failed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=4))
        self.system.execute_jobs()
        self.assertReports(started={1: 4}, retried={1: 3}, failed={1: 1})

    def test_backup___when_job_retries_itself_and_then_runs_backup___reports_completed_backup_instead(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=4, backup_job=TestJob(2)))
        self.system.execute_jobs()
        self.assertReports(started={1: 4, 2: 1}, completed={2: 1}, retried={1: 4}, failed={})

    def test_backup___when_job_retries_itself_and_then_runs_backup_but_it_also_fails___reports_failed_backup(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=4, backup_job=TestJob(2, fails=4)))
        self.system.execute_jobs()
        self.assertReports(started={1: 4, 2: 4}, retried={1: 4, 2: 3}, failed={2: 1})

    def test_failed___when_job_raises_exception_and_system_is_fault_tolerant___and_throws_when_system_has_fail_gracefully_policy_instead(self):
        def prepare():
            self.system.register_worker(1, TestWorker(self.system))
            self.system.push_job(TestJob(1, raises=True))

        self.system = self.sut(fail=JobFailPolicy.FAULT_TOLERANT)
        prepare()
        self.system.execute_jobs()
        self.assertReports(started={1: 4}, retried={1: 3}, failed={1: 1}, errors=4)

        self.system = self.sut(fail=JobFailPolicy.FAIL_GRACEFULLY)
        prepare()
        with self.assertRaises(Exception) as context:
            self.system.execute_jobs()

        self.assertIsInstance(context.exception, Exception)

    def test_retries___when_job_retries_previous_job___reports_completed_jobs_and_retries(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.push_job(TestJob(1, next_job=TestJob(2, fails=1, retry_job=TestJob(1, next_job=TestJob(2)))))
        self.system.execute_jobs()
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
        self.system.execute_jobs()
        self.assertReports(completed={1: 4}, started={1: 4, 2: 4}, retried={2: 3}, failed={2: 1})

    def test_cancel_pending_jobs___reports_completed_jobs_until_that_point_and_proper_pending_amount___then_resuming_works_as_expected(self):
        self.system.register_worker(1, TestWorker(self.system))
        self.system.register_worker(2, TestWorker(self.system))
        self.system.register_worker(3, TestWorker(self.system))
        self.system.register_worker(4, TestWorker(self.system))

        self.system.push_job(TestJob(1, next_job=(TestJob(2, cancel_pending_jobs=True, next_job=(TestJob(3, next_job=TestJob(4)))))))

        self.system.execute_jobs()
        self.assertReports(completed={1: 1, 2: 1})

        self.reporter.reset()
        self.system.push_job(TestJob(1, next_job=(TestJob(2, cancel_pending_jobs=False, next_job=(TestJob(3, next_job=TestJob(4)))))))

        self.system.execute_jobs()
        self.assertReports(completed={1: 1, 2: 1, 3: 1, 4: 1})

    def test_throwing_reporter_during_retries___does_not_incur_in_infinite_loop(self):
        class TestThrowingReporter(TestProgressReporter):
            def notify_job_retried(self, _job: Job, _retry_job: Job, _exception: BaseException):
                raise Exception('Houston, we have a problem.')

        self.reporter = TestThrowingReporter()
        self.system = self.sut(fail=JobFailPolicy.FAULT_TOLERANT)

        self.system.register_worker(1, TestWorker(self.system))
        self.system.push_job(TestJob(1, fails=3))

        self.system.execute_jobs()

        self.assertReports(completed={1: 1}, started={1: 4}, errors=3)

    def test_execute_jobs_with_just_1_thread___reports_completed_jobs(self):
        self.system.register_worker(1, TestWorker(self.system))

        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))
        self.system.push_job(TestJob(1))

        self.assertEqual(self.system.pending_jobs_amount(), 3)
        self.system.execute_jobs()

        self.assertReports(completed={1: 3}, started={1: 3})

    def test_timeout___depends_on_activity_tracker(self):
        for tracker, timed_out in [(None, True), (ActivityTracker().track(float('inf')), False)]:
            self.setUp()
            with self.subTest(tracker=tracker):
                clock = [0.0]
                def fake_monotonic():
                    clock[0] += 1.0
                    return clock[0]

                self.system = self.sut(fail=JobFailPolicy.FAULT_TOLERANT, activity_tracker=tracker, time_monotonic=fake_monotonic, timeout=0)
                self.system.register_worker(1, TestWorker(self.system))
                self.system.push_job(TestJob(1))
                self.system.execute_jobs()
                self.assertReports(completed={1: 1}, timed_out=timed_out)

    def test_job_add_tag_a_b___when_checked_tags___returns_b(self):
        job = TestJob(1)
        job.add_tag('a')
        job.add_tag('b')
        self.assertEqual(['a', 'b'], sorted(job.tags))

    def test_job_add_tag_a___when_checking_tag_a_and_b___returns_true_and_false_respectively(self):
        job = TestJob(1)
        job.add_tag('a')
        self.assertTrue(job.has_tag('a'))
        self.assertFalse(job.has_tag('b'))

    def assertReports(self,
        completed: Optional[Dict[int, int]] = None,
        started: Optional[Dict[int, int]] = None,
        in_progress: Optional[Dict[int, int]] = None,
        failed: Optional[Dict[int, int]] = None,
        retried: Optional[Dict[int, int]] = None,
        cancelled: Optional[Dict[int, int]] = None,
        pending: int = 0,
        timed_out: bool = False,
        errors: int = 0
    ):
        self.assertEqual({
            'started_jobs': started or completed or {},
            'in_progress_jobs': in_progress or {},
            'completed_jobs': completed or {},
            'failed_jobs': failed or {},
            'retried_jobs': retried or {},
            'cancelled_jobs': cancelled or {},
            'pending_jobs_amount': pending,
            'timed_out': timed_out,
            'errors': errors
        }, {
            'started_jobs': self.reporter.started_jobs,
            'in_progress_jobs': {k: len(v) for k, v in self.reporter.tracker.in_progress.items() if len(v) != 0},
            'completed_jobs': self.reporter.completed_jobs,
            'failed_jobs': self.reporter.failed_jobs,
            'retried_jobs': self.reporter.retried_jobs,
            'cancelled_jobs': self.reporter.cancelled_jobs,
            'pending_jobs_amount': self.system.pending_jobs_amount(),
            'timed_out': self.system.timed_out(),
            'errors': len(self.system.get_unhandled_exceptions())
        })


class TestJob(Job):
    def __init__(self, type_id: int, next_job: Optional['TestJob'] = None, retry_job: Optional['TestJob'] = None, backup_job: Optional['TestJob'] = None, fails: int = 0, register_worker: Optional[Worker] = None,
                 cancel_pending_jobs: bool = False, raises: bool = False, execute_jobs: bool = False, set_signals: Optional[List[signal.Signals]] = None):
        self._type_id = type_id
        self._retry_job = retry_job
        self._backup_job = backup_job
        self.next_job = next_job
        self.fails = fails
        self.raises = raises
        self.execute_jobs = execute_jobs
        self.register_worker = register_worker
        self.set_signals = set_signals
        self.cancel_pending_jobs = cancel_pending_jobs

    @property
    def type_id(self) -> int:
        return self._type_id

    def retry_job(self):
        if self._retry_job is not None:
            return self._retry_job

        return super().retry_job()

    def backup_job(self):
        if self._backup_job is not None:
            return self._backup_job

        return super().backup_job()


class TestWorker(Worker):
    def __init__(self, system: JobSystem):
        self.system = system

    def operate_on(self, job: TestJob) -> WorkerResult:
        if job.fails > 0:
            job.fails -= 1
            return [], Exception('Fails!')

        if job.raises:
            raise Exception('Raises!')

        if job.cancel_pending_jobs:
            self.system.cancel_pending_jobs()

        if job.register_worker is not None:
            self.system.register_worker(99, job.register_worker)

        if job.set_signals is not None:
            self.system.set_interfering_signals(job.set_signals)

        if job.execute_jobs:
            self.system.execute_jobs()

        if job.next_job is not None:
            return [job.next_job], None

        return [], None


