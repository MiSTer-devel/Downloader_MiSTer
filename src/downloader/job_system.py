# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>
import sys
import time
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

from abc import abstractmethod, ABC
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Dict, Optional, Callable, List, Tuple, Any
import queue
import threading
import logging
import signal

_thread_local_storage = threading.local()


class JobSystem:
    _next_job_type_id: int = 0

    @staticmethod
    def get_job_type_id() -> int:
        JobSystem._next_job_type_id += 1
        return JobSystem._next_job_type_id

    def __init__(self, reporter: 'ProgressReporter', max_threads: int = 6, max_tries: int = 3, wait_timeout: float = 0.1):
        self._max_threads: int = max_threads
        self._max_tries: int = max_tries
        self._wait_timeout: float = wait_timeout
        self._reporter: ProgressReporter = reporter
        self._lock = threading.Lock()
        self._job_queue: queue.PriorityQueue['_JobPackage'] = queue.PriorityQueue()
        self._workers: Dict[int, 'Worker'] = {}
        self._pending_jobs_amount: int = 0
        self._pending_jobs_cancelled: bool = False
        self._is_accomplishing_jobs: bool = False
        self._package_parents: Dict[int, _JobPackage] = {}
        self._jobs_pushed = 0

    def pending_jobs_amount(self) -> int:
        return self._pending_jobs_amount

    def register_worker(self, job_id: int, worker: 'Worker') -> None:
        if self._is_accomplishing_jobs:
            raise CantRegisterWorkerException('Can not register workers while accomplishing jobs')
        self._workers[job_id] = worker

    def push_job(self, job: 'Job', priority: Optional[int] = None) -> None:
        worker = self._get_worker(job)
        parent_package: Optional[_JobPackage] = getattr(_thread_local_storage, 'current_package', None)
        self._jobs_pushed += 1
        self._job_queue.put(_JobPackage(
            job=job,
            worker=worker,
            tries=0 if parent_package is None else parent_package.tries,
            priority=priority or self._jobs_pushed,
            parent=parent_package
        ))
        with self._lock:
            self._pending_jobs_amount += 1

    def cancel_pending_jobs(self) -> None:
        with self._lock:
            self._pending_jobs_cancelled = True

    def accomplish_pending_jobs(self) -> None:
        if self._is_accomplishing_jobs:
            raise CantAccomplishJobs('Can not call to accomplish jobs when its already running.')

        self._is_accomplishing_jobs = True
        self._pending_jobs_cancelled = False
        try:
            if self._max_threads > 1:
                self._accomplish_with_threads(self._max_threads)
            else:
                self._accomplish_without_threads()
        finally:
            self._is_accomplishing_jobs = False

    def _accomplish_with_threads(self, max_threads: int) -> None:
        previous_handler = signal.getsignal(signal.SIGINT)
        try:
            signal.signal(signal.SIGINT, lambda sig, frame: self._sigint_handler(previous_handler, sig, frame))

            futures = []
            notifications: queue.Queue[Tuple[bool, '_JobPackage']] = queue.Queue()
            with ThreadPoolExecutor(max_workers=max_threads) as thread_executor:
                while self._pending_jobs_amount > 0 and not self._pending_jobs_cancelled:
                    try:
                        package = self._job_queue.get(timeout=self._wait_timeout)
                    except queue.Empty:
                        package = None

                    if package is not None:
                        self._assert_there_are_no_cycles(package)
                        future = thread_executor.submit(self._operate_on_next_job, package, notifications)
                        futures.append((package, future))

                    self._handle_notifications(notifications)
                    futures = self._handle_futures(futures)
                    self._report_work_in_progress()
                    sys.stdout.flush()

            self._handle_notifications(notifications)
            self._handle_futures(futures)
        finally:
            signal.signal(signal.SIGINT, previous_handler)

    def _accomplish_without_threads(self) -> None:
        notifications: queue.Queue[Tuple[bool, '_JobPackage']] = queue.Queue()
        while self._pending_jobs_amount > 0 and not self._pending_jobs_cancelled and not self._job_queue.empty():
            package = self._job_queue.get(block=False)
            self._job_queue.task_done()
            if package is not None:
                self._assert_there_are_no_cycles(package)
                try:
                    self._operate_on_next_job(package, notifications)
                except BaseException as e:
                    self._retry_package(package, e)

            self._handle_notifications(notifications)
            self._report_work_in_progress()

        self._handle_notifications(notifications)

    @staticmethod
    def _operate_on_next_job(package: '_JobPackage', notifications: queue.Queue[Tuple[bool, '_JobPackage']]) -> None:
        try:
            _thread_local_storage.current_package = package

            job, worker = package.job, package.worker
            notifications.put((False, package))

            worker.operate_on(job)

            notifications.put((True, package))
        finally:
            del _thread_local_storage.current_package

    def _retry_package(self, package: '_JobPackage', e: BaseException) -> None:
        if isinstance(e, JobSystemAbortException):
            raise e
        should_retry = package.tries < self._max_tries
        if should_retry:
            retry_job = package.job.retry_job()
            self._job_queue.put(_JobPackage(
                job=retry_job,
                worker=self._get_worker(retry_job),
                tries=package.tries + 1,
                priority=package.priority
            ))
        else:
            self._pending_jobs_amount -= 1
        try:
            if should_retry:
                self._report_job_retried(package, e)
            else:
                self._report_job_failed(package, e)
        except ReportException as report_exception:
            logger = logging.getLogger()
            logger.exception(e)
            logger.exception(report_exception)

    def _get_worker(self, job: 'Job') -> 'Worker':
        worker = self._workers.get(job.type_id, None)
        if worker is None:
            raise NoWorkerException(f'No worker registered for job type id {job.type_id}')
        return worker

    def _handle_notifications(self, notification_queue: queue.Queue[Tuple[bool, '_JobPackage']]) -> None:
        while not notification_queue.empty():
            notification = notification_queue.get(block=False)
            notification_queue.task_done()

            completed, package = notification
            if completed:
                self._pending_jobs_amount -= 1
                self._report_job_completed(package)
            else:
                self._report_job_started(package)

    def _handle_futures(self, futures: List[Tuple['_JobPackage', Future[None]]]) -> List[Tuple['_JobPackage', Future[None]]]:
        still_pending = []
        for package, future in futures:
            if future.done():
                future_exception = future.exception()
                if future_exception:
                    self._retry_package(package, future_exception)
            else:
                still_pending.append((package, future))
        return still_pending

    def _assert_there_are_no_cycles(self, package: '_JobPackage') -> None:
        parent_package = package.parent
        if parent_package is None:
            return

        job = package.job
        seen = set()
        current = parent_package

        while current is not None:
            if current.job.type_id in seen:
                raise CycleDetectedException(f'Can not push Job {package.job.type_id} because it introduced a cycle')

            seen.add(current.job.type_id)
            with self._lock:
                current = self._package_parents.get(current.job.type_id)

        if parent_package is not None:
            with self._lock:
                self._package_parents[job.type_id] = parent_package

    def _sigint_handler(self, previous_handler: Any, sig: Any, frame: Any) -> None:
        print('SHUTTING DOWN, PLEASE WAIT...')
        self.cancel_pending_jobs()
        if previous_handler is not None:
            previous_handler(sig, frame)

    def _report_job_started(self, package: '_JobPackage') -> None:
        self._try_report('started', lambda: self._reporter_for_package(package).notify_job_started(package.job))

    def _report_job_completed(self, package: '_JobPackage') -> None:
        self._try_report('completed', lambda: self._reporter_for_package(package).notify_job_completed(package.job))

    def _report_job_retried(self, package: '_JobPackage', e: BaseException) -> None:
        self._try_report('retried', lambda: self._reporter_for_package(package).notify_job_retried(package.job, e))

    def _report_job_failed(self, package: '_JobPackage', e: BaseException) -> None:
        self._try_report('failed', lambda: self._reporter_for_package(package).notify_job_failed(package.job, e))

    def _report_work_in_progress(self) -> None:
        self._try_report('in progress', lambda: self._reporter.notify_work_in_progress())

    def _try_report(self, context: str, cb: Callable[[], None]) -> None:
        try:
            cb()
        except Exception as e:
            raise ReportException(f'CRITICAL! Exception while reporting job {context}: {e}') from e

    def _reporter_for_package(self, package: '_JobPackage') -> 'ProgressReporter':
        return package.worker.reporter() or self._reporter


class JobSystemAbortException(Exception): pass
class CycleDetectedException(JobSystemAbortException): pass
class NoWorkerException(JobSystemAbortException): pass
class CantRegisterWorkerException(JobSystemAbortException): pass
class CantAccomplishJobs(JobSystemAbortException): pass
class ReportException(Exception): pass


class Job(ABC):
    @property
    @abstractmethod
    def type_id(self) -> int:
        """Returns the job type id"""

    def retry_job(self) -> 'Job':
        return self


class Worker(ABC):
    @abstractmethod
    def operate_on(self, job: Job) -> None:
        """Handles the job."""

    def reporter(self) -> Optional['ProgressReporter']:
        """Different progress reporter for the jobs operated by this worker."""
        return None


class ProgressReporter(ABC):
    @abstractmethod
    def notify_job_started(self, job: Job) -> None:
        """Called when a job is started. Must not throw exceptions."""

    @abstractmethod
    def notify_work_in_progress(self) -> None:
        """Called after each loop."""

    @abstractmethod
    def notify_job_completed(self, job: Job) -> None:
        """Called when a job is completed. Must not throw exceptions."""

    @abstractmethod
    def notify_job_failed(self, job: Job, exception: BaseException) -> None:
        """Called when a job fails. Must not throw exceptions."""

    @abstractmethod
    def notify_job_retried(self, job: Job, exception: BaseException) -> None:
        """Called when a job is retried. Must not throw exceptions."""


@dataclass
class _JobPackage:
    job: Job
    worker: Worker
    tries: int
    priority: int
    parent: Optional['_JobPackage'] = None

    def __lt__(self, other: '_JobPackage') -> bool:
        return self.priority < other.priority
