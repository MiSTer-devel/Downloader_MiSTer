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
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum, auto
from contextlib import contextmanager
import traceback
from types import FrameType
from typing import Deque, Dict, Optional, Callable, List, Tuple, Any, Iterable, Protocol, Union
import sys
import time
import queue
import threading
import signal


class JobContext(Protocol):
    """A context for workers to interact with the job system in a thread-safe manner."""

    def cancel_pending_jobs(self) -> None:
        """Allows a worker to cancel all pending jobs."""

    def wait_for_other_jobs(self) -> None:
        """Allows a worker to wait for other jobs to progress."""


class JobSystem(JobContext):
    """Processes jobs through workers concurrently. Workers must use the JobContext interface. Other methods are not thread-safe."""

    _next_job_type_id: int = 0

    @staticmethod
    def get_job_type_id() -> int:
        JobSystem._next_job_type_id += 1
        return JobSystem._next_job_type_id

    def __init__(self, reporter: 'ProgressReporter', logger: 'JobSystemLogger', max_threads: int = 6, max_tries: int = 3, wait_timeout: float = 0.1, max_cycle: int = 3, max_timeout: float = 300, retry_unexpected_exceptions: bool = True, raise_report_exceptions: bool = False):
        self._reporter: ProgressReporter = reporter
        self._logger: JobSystemLogger = logger
        self._max_threads: int = max_threads
        self._max_tries: int = max_tries
        self._wait_timeout: float = wait_timeout
        self._max_cycle: int = max_cycle
        self._max_timeout: float = max_timeout
        self._retry_unexpected_exceptions: bool = retry_unexpected_exceptions
        self._raise_report_exceptions: bool = raise_report_exceptions
        self._job_queue: Deque[_JobPackage] = deque()
        self._unhandled_errors: List[BaseException] = []
        self._notifications: queue.Queue[Tuple[_JobState, _JobPackage, Optional[_JobError]]] = queue.Queue()
        self._jobs_cancelled: List[Job] = []
        self._workers: Dict[int, Worker] = {}
        self._lock = threading.Lock()
        self._pending_jobs_amount: int = 0
        self._are_jobs_cancelled: bool = False
        self._is_executing_jobs: bool = False
        self._timeout_clock: float = 0
        self._timed_out: bool = False
        self._signals = [signal.SIGINT]

    def timed_out(self) -> bool: return self._timed_out
    def pending_jobs_amount(self) -> int: return self._pending_jobs_amount

    def set_interfering_signals(self, signals: List[signal.Signals]):
        with self._lock:
            if self._is_executing_jobs: raise CantSetSignalsException('Can not set interfering signals while executing jobs')

        self._signals = signals

    def register_worker(self, job_id: int, worker: 'Worker') -> None:
        self.register_workers({job_id: worker})

    def register_workers(self, workers: Dict[int, 'Worker']) -> None:
        with self._lock:
            if self._is_executing_jobs: raise CantRegisterWorkerException('Can not register workers while executing jobs')

            self._workers.update(workers)

    def push_job(self, job: 'Job') -> None:
        with self._lock:
            if self._is_executing_jobs: raise CantPushJobs('Can not push more jobs while executing jobs')

        error = self._internal_push_job(job, parent_package=None)
        if error is not None: raise error

    def execute_jobs(self) -> None:
        """This function executes all the jobs with the registered workers. It must be used in the MAIN THREAD."""
        with self._lock:
            if self._is_executing_jobs: raise CantExecuteJobs('Can not call to execute jobs when its already running.')

            self._is_executing_jobs = True
            self._are_jobs_cancelled = False

        self._timed_out = False
        self._jobs_cancelled.clear()
        self._unhandled_errors.clear()
        self._update_timeout_clock()

        try:
            if self._max_threads > 1:
                self._execute_with_threads(self._max_threads)
            else:
                self._execute_without_threads()

            self._handle_notifications()
            self._jobs_cancelled.extend([p.job for p in self._job_queue])
            self._job_queue.clear()
            if self._jobs_cancelled:
                self._record_jobs_cancelled(self._jobs_cancelled)
            self._handle_unhandled_exceptions(self._unhandled_errors)
        finally:
            with self._lock:
                self._is_executing_jobs = False

    def cancel_pending_jobs(self) -> None:
        # This must be thread-safe. We lock so that execution can be interrupted asap.

        with self._lock:
            self._are_jobs_cancelled = True

    def wait_for_other_jobs(self):
        # This must be thread-safe. But we don't need to lock next two checks, because
        # we are only reading and we are fine with eventual consistency here.

        if self._timed_out: raise CantWaitWhenTimedOut('Can not wait when timed out')
        if not self._is_executing_jobs: raise CantWaitWhenNotExecutingJobs('Can not wait when not executing jobs')

        if self._max_threads > 1:
            time.sleep(self._wait_timeout)
        else:
            # This branch does not need to be thread-safe at all, since concurrency is off.
            self._check_clock()
            self._execute_without_threads(just_one_tick=True)

    def _internal_push_job(self, job: 'Job', parent_package: Optional['_JobPackage']) -> Optional[Exception]:
        worker = self._workers.get(job.type_id, None)
        if worker is None:
            return CantPushJobs(f'Push job failed because no worker is registered for job type id "{job.type_id}" and name "{job.__class__.__name__}"')

        package = _JobPackage(
            job=job,
            worker=worker,
            tries=0 if parent_package is None else parent_package.tries,
            parent=parent_package,
            next_jobs=None
        )
        if job.priority:
            self._job_queue.appendleft(package)
        else:
            self._job_queue.append(package)
        self._pending_jobs_amount += 1
        return None

    def _execute_with_threads(self, max_threads: int) -> None:
        with self._temporary_signal_handlers(), ThreadPoolExecutor(max_workers=max_threads) as thread_executor:
            futures = []
            while self._pending_jobs_amount > 0 and self._are_jobs_cancelled is False:
                package = self._job_queue.popleft() if self._job_queue else None
                if package is not None:
                    self._assert_there_are_no_cycles(package)
                    if not self._unhandled_errors:
                        future = thread_executor.submit(self._operate_on_next_job, package, self._notifications)
                        futures.append((package, future))

                self._handle_notifications()
                futures = self._remove_done_futures(futures)
                self._record_work_in_progress()
                self._check_clock()
                sys.stdout.flush()
                if self._unhandled_errors:
                    self._are_jobs_cancelled = True

            if self._are_jobs_cancelled:
                self._record_jobs_cancelled([])
                self._cancel_futures(futures)

    def _execute_without_threads(self, just_one_tick: bool = False) -> None:
        while self._pending_jobs_amount > 0 and self._are_jobs_cancelled is False:
            package = self._job_queue.popleft() if self._job_queue else None
            if package is not None:
                self._assert_there_are_no_cycles(package)
                if not self._unhandled_errors:
                    try:
                        self._operate_on_next_job(package, self._notifications)
                    except BaseException as e:
                        self._handle_raised_exception(package, e)

                    self._handle_notifications()

            self._record_work_in_progress()
            self._check_clock()
            if just_one_tick: return
            if self._unhandled_errors:
                self._are_jobs_cancelled = True

    def _operate_on_next_job(self, package: '_JobPackage', notifications: queue.Queue[Tuple['_JobState', '_JobPackage', Optional['_JobError']]]) -> None:
        if self._are_jobs_cancelled:
            notifications.put((_JobState.JOB_CANCELLED, package, None))
            return

        job, worker = package.job, package.worker
        notifications.put((_JobState.JOB_STARTED, package, None))

        jobs, error = worker.operate_on(job)

        if error is not None:
            notifications.put((_JobState.NIL, package, _JobError(error)))
        else:
            package.next_jobs = jobs
            notifications.put((_JobState.JOB_COMPLETED, package, None))

    def _retry_package(self, package: '_JobPackage') -> bool:
        retry_job = package.job.retry_job()
        if package.tries >= self._max_tries or retry_job is None:
            return False

        worker = self._workers.get(retry_job.type_id, None)
        if worker is None:
            self._unhandled_errors.append(CantPushJobs(f'Retry failed because there no worker is registered for job type id "{retry_job.type_id}" and name "{retry_job.__class__.__name__}"'))
            return False

        retry_package = _JobPackage(
            job=retry_job,
            worker=worker,
            tries=package.tries + 1,
            parent=None,
            next_jobs=package.next_jobs
        )
        if retry_job.priority:
            self._job_queue.appendleft(retry_package)
        else:
            self._job_queue.append(retry_package)

        return True

    def _handle_notifications(self) -> None:
        while True:
            try:
                notification = self._notifications.get(block=False)
            except queue.Empty:
                break

            status, package, error = notification
            if error is not None:
                if not self._are_jobs_cancelled and self._retry_package(package):
                    self._record_job_retried(package, error.child)
                else:
                    self._record_job_failed(package, error.child)
            elif status == _JobState.JOB_COMPLETED:
                next_jobs = []
                if not self._are_jobs_cancelled:
                    norm_next_jobs = _normalize_jobs(package.next_jobs)
                    for child_job in norm_next_jobs:
                        error = self._internal_push_job(child_job, parent_package=package)
                        if error is None:
                            next_jobs.append(child_job)
                        else:
                            self._unhandled_errors.append(error)

                self._record_job_completed(package, next_jobs)
            elif status == _JobState.JOB_STARTED:
                self._record_job_started(package)
            elif status == _JobState.JOB_CANCELLED:
                self._jobs_cancelled.append(package.job)
            else: assert False, f'Unhandled JobState notification: {status}'

    def _remove_done_futures(self, futures: List[Tuple['_JobPackage', Future[None]]]) -> List[Tuple['_JobPackage', Future[None]]]:
        still_pending = []
        for package, future in futures:
            if future.done():
                e = future.exception()
                if e is not None:
                    self._handle_raised_exception(package, e)
            else:
                still_pending.append((package, future))
        return still_pending

    def _cancel_futures(self, futures: List[Tuple['_JobPackage', Future[None]]]) -> None:
        for package, future in futures:
            if future.cancel():
                self._jobs_cancelled.append(package.job)
            else:
                e = future.exception()
                if e is None: continue

                self._logger.print(f'Unexpected exception "{type(e).__name__}" while canceling job {package.job.type_id}|{package.job.__class__.__name__}: {e}')
                self._record_job_failed(package, _wrap_unknown_base_error(e))

    def _handle_raised_exception(self, package: '_JobPackage', e: BaseException):
        if isinstance(e, JobSystemAbortException):
            self._logger.print(f'Unexpected system abort while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {e}')
            self._record_job_failed(package, e)
            self._unhandled_errors.append(e)
            return

        e = _wrap_unknown_base_error(e)

        if not self._retry_unexpected_exceptions:
            self._record_job_failed(package, e)
            self._unhandled_errors.append(UnknownException(f"Could not handle '{type(e).__name__}' exception", e))
            return

        self._logger.print(f'Handling unexpected exception "{type(e).__name__}" while operating on job {package.job.type_id}|{package.job.__class__.__name__}: {e}')

        if self._retry_package(package):
            self._record_job_retried(package, e)
        else:
            self._record_job_failed(package, e)

    def _handle_unhandled_exceptions(self, errors: List[BaseException]) -> None:
        if not errors: return

        self._logger.debug(f'\nUnhandled Exceptions: {len(errors)}\n')
        for e in errors[:0:-1]:
            traceback_str = ''.join(traceback.TracebackException.from_exception(e).format()) + '\n'
            self._logger.debug(traceback_str)

        e = errors[0]
        cause = getattr(e, 'cause', None)
        if cause is not None: raise e from cause
        else: raise e

    def _update_timeout_clock(self) -> None:  # We only want to update the timeout when the state of the job pipeline changes
        self._timeout_clock = time.monotonic() + self._max_timeout

    def _check_clock(self) -> None:
        if self._timeout_clock > time.monotonic():
            return

        self._timed_out = True
        self._are_jobs_cancelled = True
        self._logger.print(f'WARNING! Jobs timeout reached after {self._max_timeout} seconds!')

    def _assert_there_are_no_cycles(self, package: '_JobPackage') -> None:
        parent_package = package.parent
        if parent_package is None:
            return

        seen: Dict[int, int] = dict()
        current: Optional[_JobPackage] = parent_package

        while current is not None:
            seen_value = seen.get(current.job.type_id, 0)
            if seen_value >= self._max_cycle:
                self._unhandled_errors.append(CycleDetectedException(f'Can not use Job {package.job.type_id}|{package.job.__class__.__name__} because it introduced a cycle of length {seen_value}'))
                return

            seen[current.job.type_id] = seen_value + 1
            current = current.parent

    @contextmanager
    def _temporary_signal_handlers(self):
        previous_handlers = [(s, signal.getsignal(s)) for s in self._signals]
        try:
            for sig1, cb in previous_handlers:
                signal.signal(sig1, lambda sig2, frame: self._signal_handler(cb, sig2, frame))
            yield
        finally:
            for sig, cb in previous_handlers: signal.signal(sig, cb)

    def _signal_handler(self, previous_handler: Union[Callable[[int, Optional[FrameType]], Any], int, None], sig: int, frame: Optional[FrameType]) -> None:
        try:
            self._logger.print(f"SIGNAL '{signal.strsignal(sig)}' RECEIVED!")
            for thread_name, stack in stacks_from_all_threads().items():
                self._logger.debug(f"Thread: {thread_name} [{len(stack)}]")
                for entry in stack: self._logger.debug(f"  {entry['file']}:{entry['line']} ({entry['func']})")
            self._logger.print('SHUTTING DOWN...')
            self._are_jobs_cancelled = True
        except Exception as e:
            self._logger.print('CANCELING PENDING JOBS FAILED!', sig, e)
        try:
            if callable(previous_handler) and previous_handler not in (signal.SIG_IGN, signal.SIG_DFL):
                previous_handler(sig, frame)
        except Exception as e:
            self._logger.print('PREVIOUS HANDLER FAILED!', sig, e)

    def _record_job_started(self, package: '_JobPackage') -> None:
        self._update_timeout_clock()
        self._try_report('started', self._reporter_for_package(package).notify_job_started, package.job)

    def _record_job_completed(self, package: '_JobPackage', next_jobs: List['Job']) -> None:
        self._pending_jobs_amount -= 1
        self._update_timeout_clock()
        self._try_report('completed', self._reporter_for_package(package).notify_job_completed, package.job, next_jobs)

    def _record_job_retried(self, package: '_JobPackage', e: Exception) -> None:
        self._update_timeout_clock()
        self._try_report('retried', self._reporter_for_package(package).notify_job_retried, package.job, e)

    def _record_job_failed(self, package: '_JobPackage', e: Exception) -> None:
        self._pending_jobs_amount -= 1
        self._update_timeout_clock()
        self._try_report('failed', self._reporter_for_package(package).notify_job_failed, package.job, e)

    def _record_jobs_cancelled(self, jobs: List['Job']) -> None:
        self._update_timeout_clock()
        self._try_report('cancelled', self._reporter.notify_jobs_cancelled, jobs)

    def _record_work_in_progress(self) -> None: self._try_report('in-progress', self._reporter.notify_work_in_progress)

    def _try_report(self, context: str, method: Callable, *args) -> None:
        try: method(*args)
        except Exception as e:
            e_msg = f'CRITICAL! Exception while reporting job "{context}": {type(e).__name__}'
            self._logger.print(e_msg)
            self._logger.print(e)
            if self._raise_report_exceptions:
                self._unhandled_errors.append(UnknownException(e_msg, e))

    def _reporter_for_package(self, package: '_JobPackage') -> 'ProgressReporter': return package.worker.reporter() or self._reporter


class Job(ABC):
    """Base class for defining jobs."""
    __slots__ = ('_tags')

    @property
    @abstractmethod
    def type_id(self) -> int:
        """Returns the job type id"""

    def retry_job(self) -> Optional['Job']:
        return self

    def add_tag(self, tag: str) -> 'Job':
        tags = getattr(self, '_tags', None)
        if tags is None:
            self._tags = set()
        self._tags.add(tag)
        return self

    def has_tag(self, tag: str) -> bool:
        tags = getattr(self, '_tags', None)
        if tags is None: return False
        return tag in tags

    @property
    def tags(self) -> Iterable[str]:
        return getattr(self, '_tags', set())

    @property
    def priority(self): return False


WorkerResult = Tuple[Union[List[Job], Optional[Job]], Optional[Exception]]


class Worker(ABC):
    """Abstract base class for defining workers that process jobs."""

    @abstractmethod
    def operate_on(self, job: Job) -> WorkerResult:
        """Handles the job."""

    def reporter(self) -> Optional['ProgressReporter']:
        """Different progress reporter for the jobs operated by this worker."""
        return None


class ProgressReporter(Protocol):
    """Interface for reporting progress of jobs."""

    def notify_job_started(self, job: Job) -> None:
        """Called when a job is started. Must not throw exceptions."""

    def notify_work_in_progress(self) -> None:
        """Called after each loop."""

    def notify_jobs_cancelled(self, jobs: List[Job]) -> None:
        """Called when all pending jobs are cancelled."""

    def notify_job_completed(self, job: Job, next_jobs: List[Job]) -> None:
        """Called when a job is completed. Must not throw exceptions."""

    def notify_job_failed(self, job: Job, exception: Exception) -> None:
        """Called when a job fails. Must not throw exceptions."""

    def notify_job_retried(self, job: Job, exception: Exception) -> None:
        """Called when a job is retried. Must not throw exceptions."""


class JobSystemAbortException(Exception): pass
class CantRegisterWorkerException(JobSystemAbortException): pass
class CantSetSignalsException(JobSystemAbortException): pass
class CantExecuteJobs(JobSystemAbortException): pass
class CantPushJobs(JobSystemAbortException): pass
class CantWaitWhenNotExecutingJobs(JobSystemAbortException): pass
class CantWaitWhenTimedOut(JobSystemAbortException): pass
class CycleDetectedException(JobSystemAbortException): pass
class UnknownException(JobSystemAbortException):
    def __init__(self, message: str, cause: BaseException):
        super().__init__(message)
        self.cause = cause

class JobSystemLogger(Protocol):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True): """Prints a message to the logger."""
    def debug(self, *args, sep='', end='\n', flush=True): """Prints a debug message to the logger."""


@dataclass(eq=False, order=False)
class _JobPackage:
    __slots__ = ('job', 'worker', 'tries', 'next_jobs', 'parent')

    job: Job
    worker: Worker
    tries: int
    next_jobs: Union[Optional[Job], List[Job]]
    parent: Optional['_JobPackage']

    # Consider removing __str__ at least in non-debug environments
    def __str__(self): return f'JobPackage(job_type_id={self.job.type_id}, job_class={self.job.__class__.__name__}, tries={self.tries})'

def _normalize_jobs(jobs: Optional[Union[Job, List[Job]]]) -> List[Job]:
    if jobs is None:
        return []
    elif isinstance(jobs, Job):
        return [jobs]
    else:
        return jobs

class _JobError(Exception):
    def __init__(self, child: Exception):
        super().__init__(child)
        self.child = child

def _wrap_unknown_base_error(e: BaseException) -> Exception:
    if isinstance(e, Exception): return e
    wrapper = Exception(f"Unknown base error: {type(e).__name__}")
    wrapper.__cause__ = e
    return wrapper

class _JobState(Enum):
    NIL = auto()
    JOB_STARTED = auto()
    JOB_COMPLETED = auto()
    JOB_CANCELLED = auto()

def stacks_from_all_threads() -> dict:
    try:
        current_frames = sys._current_frames()
    except Exception as _e:
        return {}

    thread_stacks = {}
    for thread in threading.enumerate():
        if thread.ident not in current_frames: continue
        stack = []
        current_frame: Optional[FrameType] = current_frames[thread.ident]
        while current_frame:
            stack.append({
                "file": current_frame.f_code.co_filename,
                "line": current_frame.f_lineno,
                "func": current_frame.f_code.co_name
            })
            current_frame = current_frame.f_back

        thread_stacks[thread.name] = stack[::-1]

    return thread_stacks
