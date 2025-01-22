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

from abc import abstractmethod, ABC
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from types import FrameType
from typing import Dict, Optional, Callable, List, Tuple, Any, Iterable, Protocol, Union
import sys
import time
import queue
import threading
import signal


class JobContext(Protocol):
    """A context for workers to interact with the job system in a thread-safe manner."""

    def pending_jobs_amount(self) -> int:
        """Returns the amount of pending jobs."""

    def cancel_pending_jobs(self) -> None:
        """Allows a worker to cancel all pending jobs."""

    def wait_for_other_jobs(self) -> None:
        """Allows a worker to wait for other jobs to progress."""

    def any_in_progress_job_with_tags(self, tags: Iterable[str]) -> bool:
        """Returns true if any of the pending/processing jobs have one of the given tags."""


class JobSystem(JobContext):
    """Processes jobs through workers concurrently. Workers must use the JobContext interface. Other methods are not thread-safe."""

    _next_job_type_id: int = 0

    @staticmethod
    def get_job_type_id() -> int:
        JobSystem._next_job_type_id += 1
        return JobSystem._next_job_type_id

    def __init__(self, reporter: 'ProgressReporter', logger: 'JobSystemLogger', max_threads: int = 6, max_tries: int = 3, wait_timeout: float = 0.1, max_cycle: int = 3, max_timeout: int = 300, retry_unexpected_exceptions: bool = True):
        self._reporter: ProgressReporter = reporter
        self._logger: JobSystemLogger = logger
        self._max_threads: int = max_threads
        self._max_tries: int = max_tries
        self._wait_timeout: float = wait_timeout
        self._max_cycle: int = max_cycle
        self._max_timeout: int = max_timeout
        self._retry_unexpected_exceptions: bool = retry_unexpected_exceptions
        self._job_queue: queue.PriorityQueue['_JobPackage'] = queue.PriorityQueue()
        self._notifications: queue.Queue[Tuple[bool, '_JobPackage']] = queue.Queue()
        self._workers: Dict[int, 'Worker'] = {}
        self._lock = threading.Lock()
        self._pending_jobs_amount: int = 0
        self._pending_jobs_cancelled: bool = False
        self._is_executing_jobs: bool = False
        self._tag_dict: Dict[str, int] = defaultdict(int)
        self._jobs_pushed: int = 0
        self._timeout_clock: int = 0
        self._signals = [signal.SIGINT]

    def set_interfering_signals(self, signals: List[signal.Signals]):
        self._signals = signals

    def register_worker(self, job_id: int, worker: 'Worker') -> None:
        self.register_workers([(job_id, worker)])

    def register_workers(self, workers: Iterable[Tuple[int, 'Worker']]) -> None:
        with self._lock:
            if self._is_executing_jobs:
                raise CantRegisterWorkerException('Can not register workers while executing jobs')

            for job_id, worker in workers:
                self._workers[job_id] = worker

    def execute_jobs(self) -> None:
        """This function executes all the jobs with the registered workers. It must be used in the MAIN THREAD."""
        with self._lock:
            if self._is_executing_jobs:
                raise CantExecuteJobs('Can not call to execute jobs when its already running.')

            self._is_executing_jobs = True
            self._pending_jobs_cancelled = False

        self._update_timeout_clock()
        try:
            if self._max_threads > 1:
                self._execute_with_threads(self._max_threads)
            else:
                self._execute_without_threads()
        finally:
            with self._lock:
                self._is_executing_jobs = False

    def push_job(self, job: 'Job') -> None:
        with self._lock:
            if self._is_executing_jobs:
                raise CantPushJobs('Can not push more jobs while executing jobs')

        self._internal_push_job(job)

    def _internal_push_job(self, job: 'Job', parent_package: Optional['_JobPackage'] = None) -> None:
        worker = self._get_worker(job)
        self._jobs_pushed += 1
        package = _JobPackage(
            job=job,
            worker=worker,
            tries=0 if parent_package is None else parent_package.tries,
            priority=job.priority or self._jobs_pushed,
            parent=parent_package,
            next_jobs=None
        )
        self._job_queue.put(package)
        self._increase_jobs_amount(job)

    def pending_jobs_amount(self) -> int:
        # This must be thread-safe, and no need lock since we don't need to return the strict value.
        # Eventually the returned value will be correct upon repeating calls.
        return self._pending_jobs_amount

    def cancel_pending_jobs(self) -> None:
        # This must be thread-safe. We lock so that execution can be interrupted asap.

        with self._lock:
            self._pending_jobs_cancelled = True
            self._report_cancelled_pending_jobs()

    def wait_for_other_jobs(self):
        # This must be thread-safe. We lock because we need the strict value of _is_executing_jobs.

        with self._lock:
            if not self._is_executing_jobs:
                raise CantWaitWhenNotExecutingJobs('Can not wait when not executing jobs')

        if self._max_threads > 1:  # _max_threads is read only.
            time.sleep(self._wait_timeout)
        else:
            # This branch does not need to be thread-safe, since concurrency is off.
            self._no_threads_execute_tick()

    def any_in_progress_job_with_tags(self, tags: Iterable[str]) -> bool:
        return any(
            tag in self._tag_dict
            and self._tag_dict[tag] > 0
            for tag in tags
        )

    def _increase_jobs_amount(self, job: 'Job') -> None:
        # This method does not need to be thread-safe, since it should be called only from the main thread.

        for tag in job.tags:
            self._tag_dict[tag] += 1
        self._pending_jobs_amount += 1

    def _decrease_jobs_amount(self, job: 'Job') -> None:
        # This method does not need to be thread-safe, since it should be called only from the main thread.

        for tag in job.tags:
            self._tag_dict[tag] -= 1
        self._pending_jobs_amount -= 1

    def _execute_with_threads(self, max_threads: int) -> None:
        previous_handlers = [(s, signal.getsignal(s)) for s in self._signals]
        try:
            for sig1, cb in previous_handlers:
                signal.signal(sig1, lambda sig2, frame: self._signal_handler(cb, sig2, frame))

            futures = []
            with ThreadPoolExecutor(max_workers=max_threads) as thread_executor:
                while self._pending_jobs_amount > 0 and self._pending_jobs_cancelled is False:
                    try:
                        package = self._job_queue.get(timeout=self._wait_timeout)
                    except queue.Empty:
                        package = None

                    if package is not None:
                        self._assert_there_are_no_cycles(package)
                        future = thread_executor.submit(self._operate_on_next_job, package, self._notifications)
                        futures.append((package, future))

                    self._handle_notifications(self._notifications)
                    futures = self._handle_futures(futures)
                    self._report_work_in_progress()
                    self._check_clock()
                    sys.stdout.flush()

                if self._pending_jobs_cancelled:
                    self._cancel_futures(futures)

            self._handle_notifications(self._notifications)
            while True:
                try:
                    package = self._job_queue.get(timeout=self._wait_timeout)
                    self._report_job_failed(package, JobCancelled(f'Cancelled: {str(package)}'))
                except queue.Empty:
                    break

        finally:
            for sig, cb in previous_handlers: signal.signal(sig, cb)

    def _execute_without_threads(self) -> None:
        notifications: queue.Queue[Tuple[bool, '_JobPackage']] = queue.Queue()
        while self._pending_jobs_amount > 0 and self._pending_jobs_cancelled is False and self._job_queue.empty() is False:
            self._no_threads_execute_tick()

        self._handle_notifications(notifications)

    def _no_threads_execute_tick(self) -> None:
        package = self._job_queue.get(block=False)
        if package is not None:
            self._assert_there_are_no_cycles(package)
            try:
                self._operate_on_next_job(package, self._notifications)
            except BaseException as e:
                self._handle_exception(package, e)

        self._handle_notifications(self._notifications)
        self._report_work_in_progress()

    def _operate_on_next_job(self, package: '_JobPackage', notifications: queue.Queue[Tuple[bool, '_JobPackage']]) -> None:
        if self._pending_jobs_cancelled:
            raise JobCancelled(f'Cancelled: {str(package)}')

        job, worker = package.job, package.worker
        notifications.put((False, package))

        jobs, error = worker.operate_on(job)
        package.next_jobs = jobs

        if error is not None:
            raise _JobError(error)

        notifications.put((True, package))

    def _retry_package(self, package: '_JobPackage', e: Exception) -> None:
        retry_job = package.job.retry_job()
        should_retry = package.tries < self._max_tries and retry_job is not None
        if should_retry:
            self._job_queue.put(_JobPackage(
                job=retry_job,
                worker=self._get_worker(retry_job),
                tries=package.tries + 1,
                priority=package.priority,
                next_jobs=package.next_jobs
            ))
        else:
            self._decrease_jobs_amount(package.job)
        try:
            if should_retry:
                self._report_job_retried(package, e)
            else:
                self._report_job_failed(package, e)
        except ReportException as report_exception:
            self._logger.print('CRITICAL! Exception while reporting job failed')
            self._logger.print(e)
            self._logger.print(report_exception)

    def _get_worker(self, job: 'Job') -> 'Worker':
        worker = self._workers.get(job.type_id, None)
        if worker is None:
            raise NoWorkerException(f'No worker registered for job type id "{job.type_id}" and name "{job.__class__.__name__}"')
        return worker

    def _handle_notifications(self, notification_queue: queue.Queue[Tuple[bool, '_JobPackage']]) -> None:
        while True:
            try:
                notification = notification_queue.get(block=False)
            except queue.Empty:
                break

            completed, package = notification
            if completed:
                if isinstance(package.next_jobs, list):
                    for job in package.next_jobs:
                        self._internal_push_job(job, package)
                elif isinstance(package.next_jobs, Job):
                    self._internal_push_job(package.next_jobs, package)

                self._decrease_jobs_amount(package.job)
                self._report_job_completed(package)
            else:
                self._report_job_started(package)

    def _handle_futures(self, futures: List[Tuple['_JobPackage', Future[None]]]) -> List[Tuple['_JobPackage', Future[None]]]:
        still_pending = []
        for package, future in futures:
            if future.done():
                future_exception = future.exception()
                if future_exception is not None:
                    self._handle_exception(package, future_exception)
            else:
                still_pending.append((package, future))
        return still_pending

    def _cancel_futures(self, futures: List[Tuple['_JobPackage', Future[None]]]) -> None:
        for package, future in futures:
            if future.cancel():
                self._report_job_failed(package, JobCancelled(f'Cancelled: {str(package)}'))
            else:
                future_exception = future.exception()
                if future_exception is not None:
                    if isinstance(future_exception, Exception):
                        self._report_job_failed(package, future_exception)
                    else:
                        self._logger.print(f'CRITICAL! Unexpected exception while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {future_exception}')

    def _handle_exception(self, package: '_JobPackage', e: BaseException):
        if isinstance(e, _JobError):
            self._retry_package(package, e.child)
        elif isinstance(e, JobSystemAbortException):
            self._logger.print(f'Unexpected system abort while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {e}')
            raise e
        elif isinstance(e, Exception) and self._retry_unexpected_exceptions:
            self._logger.print(f'Unexpected exception while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {e}')
            self._retry_package(package, e)
        else:
            self._logger.print(f'CRITICAL! Unexpected exception while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {e}')
            raise e

    def _check_clock(self) -> None:
        if self._timeout_clock > time.time():
            return

        self.cancel_pending_jobs()
        self._logger.print(f'WARNING! Jobs timeout reached after {self._max_timeout} seconds!')

    def _assert_there_are_no_cycles(self, package: '_JobPackage') -> None:
        parent_package = package.parent
        if parent_package is None:
            return

        seen: Dict[int, int] = dict()
        current = parent_package

        while current is not None:
            seen_value = seen.get(current.job.type_id, 0)
            if seen_value >= self._max_cycle:
                raise CycleDetectedException(f'Can not push Job {package.job.type_id}|{package.job.__class__.__name__} because it introduced a cycle of length {seen_value}')

            seen[current.job.type_id] = seen_value + 1
            current = current.parent

    def _signal_handler(self, previous_handler: Callable[[int, Optional[FrameType]], Any], sig: int, frame: Optional[FrameType]) -> None:
        try:
            self._logger.print('SIGNAL RECEIVED!')
            self._logger.print('SHUTTING DOWN, PLEASE WAIT...')
            self.cancel_pending_jobs()
        except Exception as e:
            self._logger.print('CANCELING PENDING JOBS FAILED!', sig, e)
        try:
            if callable(previous_handler) and previous_handler not in (signal.SIG_IGN, signal.SIG_DFL):
                previous_handler(sig, frame)
        except Exception as e:
            self._logger.print('PREVIOUS HANDLER FAILED!', sig, e)

    def _update_timeout_clock(self) -> None:
        self._timeout_clock = time.time() + self._max_timeout

    def _report_job_started(self, package: '_JobPackage') -> None:
        self._try_report('started', lambda: self._reporter_for_package(package).notify_job_started(package.job))

    def _report_job_completed(self, package: '_JobPackage') -> None:
        self._try_report('completed', lambda: self._reporter_for_package(package).notify_job_completed(package.job))

    def _report_job_retried(self, package: '_JobPackage', e: Exception) -> None:
        self._try_report('retried', lambda: self._reporter_for_package(package).notify_job_retried(package.job, e))

    def _report_job_failed(self, package: '_JobPackage', e: Exception) -> None:
        self._try_report('failed', lambda: self._reporter_for_package(package).notify_job_failed(package.job, e))

    def _report_work_in_progress(self) -> None:
        self._try_report('in progress', lambda: self._reporter.notify_work_in_progress())

    def _report_cancelled_pending_jobs(self) -> None:
        self._try_report('cancelled pending jobs', lambda: self._reporter.notify_cancelled_pending_jobs())

    def _try_report(self, context: str, cb: Callable[[], None]) -> None:
        if context != 'in progress': self._update_timeout_clock()
        try:
            cb()
        except Exception as e:
            raise ReportException(f'CRITICAL! Exception while reporting job {context}: {e}') from e

    def _reporter_for_package(self, package: '_JobPackage') -> 'ProgressReporter':
        return package.worker.reporter() or self._reporter


class Job(ABC):
    """Base class for defining jobs."""

    @property
    @abstractmethod
    def type_id(self) -> int:
        """Returns the job type id"""

    def retry_job(self) -> Optional['Job']:
        return self

    def add_tag(self, tag: str) -> 'Job':
        tags = getattr(self, '_tags', None)
        if tags is None:
            tags = list()
            setattr(self, '_tags', tags)
        tags.append(tag)
        if len(tags) != len(set(tags)):
            raise CantExecuteJobs(f'Tag {tag} already added to job {self.type_id}')
        return self

    @property
    def tags(self) -> Iterable[str]:
        return getattr(self, '_tags', [])

    def set_priority(self, priority: int) -> 'Job':
        setattr(self, '_priority', priority)
        return self

    @property
    def priority(self) -> Optional[int]:
        return getattr(self, '_priority', None)


WorkerResult = Tuple[Union[List[Job], Optional[Job]], Optional[Exception]]


class Worker(ABC):
    """Abstract base class for defining workers that process jobs."""

    @abstractmethod
    def operate_on(self, job: Job) -> WorkerResult:
        """Handles the job."""

    def reporter(self) -> Optional['ProgressReporter']:
        """Different progress reporter for the jobs operated by this worker."""
        return None


class ProgressReporter(ABC):
    """Abstract base class for reporting progress of jobs."""

    @abstractmethod
    def notify_job_started(self, job: Job) -> None:
        """Called when a job is started. Must not throw exceptions."""

    @abstractmethod
    def notify_work_in_progress(self) -> None:
        """Called after each loop."""

    @abstractmethod
    def notify_cancelled_pending_jobs(self) -> None:
        """Called when all pending jobs are cancelled."""

    @abstractmethod
    def notify_job_completed(self, job: Job) -> None:
        """Called when a job is completed. Must not throw exceptions."""

    @abstractmethod
    def notify_job_failed(self, job: Job, exception: Exception) -> None:
        """Called when a job fails. Must not throw exceptions."""

    @abstractmethod
    def notify_job_retried(self, job: Job, exception: Exception) -> None:
        """Called when a job is retried. Must not throw exceptions."""


class JobSystemAbortException(Exception): pass
class CycleDetectedException(JobSystemAbortException): pass
class NoWorkerException(JobSystemAbortException): pass
class CantRegisterWorkerException(JobSystemAbortException): pass
class CantExecuteJobs(JobSystemAbortException): pass
class CantPushJobs(JobSystemAbortException): pass
class CantWaitWhenNotExecutingJobs(JobSystemAbortException): pass
class ReportException(Exception): pass
class JobCancelled(Exception): pass


class JobSystemLogger(Protocol):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """Prints a message to the logger."""


@dataclass
class _JobPackage:
    job: Job
    worker: Worker
    tries: int
    priority: int
    next_jobs: Union[Optional[Job], List[Job]]
    parent: Optional['_JobPackage'] = None

    def __lt__(self, other: '_JobPackage') -> bool: return self.priority < other.priority
    def __str__(self): return f'JobPackage(job_type_id={self.job.type_id}, job_class={self.job.__class__.__name__}, tries={self.tries}, priority={self.priority})'


class _JobError(Exception):
    def __init__(self, child: Exception):
        super().__init__(child)
        self.child = child
