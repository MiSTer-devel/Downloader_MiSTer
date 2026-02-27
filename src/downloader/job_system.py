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


class ActivityTracker:
    """Tracks worker activity to prevent false pipeline timeouts during long-running jobs."""

    def __init__(self) -> None:
        self._last_progress_time: Optional[float] = None

    def track(self, progress_time: float) -> 'ActivityTracker':
        self._last_progress_time = progress_time
        return self

    @property
    def last_progress_time(self) -> Optional[float]:
        return self._last_progress_time


class JobContext(Protocol):
    """A context for workers to interact with the job system in a thread-safe manner."""

    def cancel_pending_jobs(self) -> None:
        """Allows a worker to cancel all pending jobs."""

    def wait_for_other_jobs(self, sleep_time: float) -> None:
        """Allows a worker to wait for other jobs to progress."""


class JobFailPolicy(Enum):
    FAIL_FAST = auto()
    FAIL_GRACEFULLY = auto()
    FAULT_TOLERANT = auto()


class JobSystem(JobContext):
    """Processes jobs through workers concurrently. Workers must use the JobContext interface. Other methods are not thread-safe."""

    _next_job_type_id: int = 0

    @staticmethod
    def get_job_type_id() -> int:
        JobSystem._next_job_type_id += 1
        return JobSystem._next_job_type_id

    def __init__(self, reporter: 'ProgressReporter', logger: 'JobSystemLogger', activity_tracker: Optional[ActivityTracker] = None, time_monotonic: Callable[[], float] = time.monotonic, max_threads: int = 6, max_tries: int = 3, wait_time: float = 0.25, max_cycle: int = 3, max_timeout: float = 300, fail_policy: JobFailPolicy = JobFailPolicy.FAULT_TOLERANT) -> None:
        self._reporter: ProgressReporter = reporter
        self._logger: JobSystemLogger = logger
        self._activity_tracker: ActivityTracker = activity_tracker if activity_tracker is not None else ActivityTracker()
        self._time_monotonic = time_monotonic
        self._max_threads: int = max_threads
        self._max_tries: int = max_tries
        self._wait_time: float = wait_time
        self._max_cycle: int = max_cycle
        self._max_timeout: float = max_timeout
        self._fail_policy: JobFailPolicy = fail_policy
        self._job_queue: Deque[_JobPackage] = deque()
        self._unhandled_errors: List[BaseException] = []
        self._notifications: queue.Queue[Tuple[_JobState, _JobPackage, Optional[Exception]]] = queue.Queue()
        self._jobs_cancelled: List[Job] = []
        self._workers: Dict[int, Worker] = {}
        self._lock = threading.Lock()
        self._pending_jobs_amount: int = 0
        self._are_jobs_cancelled: bool = False
        self._is_executing_jobs: bool = False
        self._timeout_clock: float = 0
        self._timed_out: bool = False
        self._signals: List[signal.Signals] = [signal.SIGINT]

    def timed_out(self) -> bool: return self._timed_out
    def get_unhandled_exceptions(self) -> Iterable[BaseException]: return self._unhandled_errors
    def pending_jobs_amount(self) -> int: return self._pending_jobs_amount
    def are_jobs_cancelled(self) -> bool: return self._are_jobs_cancelled

    def set_interfering_signals(self, signals: List[signal.Signals]) -> None:
        with self._lock:
            if self._is_executing_jobs: raise CantSetSignalsException('Can not set interfering signals while executing jobs')

        self._signals = signals

    def register_workers(self, workers: Dict[int, 'Worker']) -> None:
        with self._lock:
            if self._is_executing_jobs: raise CantRegisterWorkerException('Can not register workers while executing jobs')

            self._workers.update(workers)

    def push_jobs(self, jobs: List['Job']) -> None:
        with self._lock:
            if self._is_executing_jobs: raise CantPushJobs('Can not push more jobs while executing jobs')

        for job in jobs:
            error = self._internal_push_job(job, parent_package=None)
            if error is not None: raise error

    def register_worker(self, job_id: int, worker: 'Worker') -> None: self.register_workers({job_id: worker})
    def push_job(self, job: 'Job') -> None: self.push_jobs([job])

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

            self._handle_notifications(False)
            self._jobs_cancelled.extend([p.job for p in self._job_queue])
            self._job_queue.clear()
            if self._jobs_cancelled:
                self._record_jobs_cancelled(self._jobs_cancelled)
            if self._fail_policy == JobFailPolicy.FAIL_GRACEFULLY:
                self._raise_unhandled_exceptions(self._unhandled_errors)
        finally:
            with self._lock:
                self._is_executing_jobs = False

    def cancel_pending_jobs(self) -> None:
        # This must be thread-safe. We lock so that execution can be interrupted asap.

        with self._lock:
            self._are_jobs_cancelled = True

    def wait_for_other_jobs(self, sleep_time: float):
        # This must be thread-safe. But we don't need to lock next two checks, because
        # we are only reading and we are fine with eventual consistency here.

        if self._timed_out: raise CantWaitWhenTimedOut('Can not wait when timed out')
        if not self._is_executing_jobs: raise CantWaitWhenNotExecutingJobs('Can not wait when not executing jobs')

        if self._max_threads > 1:
            time.sleep(sleep_time)
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
            next_jobs=[]
        )
        if job.priority:
            self._job_queue.appendleft(package)
        else:
            self._job_queue.append(package)
        self._pending_jobs_amount += 1
        return None

    def _execute_with_threads(self, max_threads: int) -> None:
        with self._temporary_signal_handlers(), ThreadPoolExecutor(max_workers=max_threads) as thread_executor:
            futures: list[Tuple['_JobPackage', Future[None]]] = [(package, thread_executor.submit(self._operate_on_next_job, package, self._notifications)) for package in self._job_queue]
            max_futures = max(max_threads * 1.5, len(futures))
            self._job_queue.clear()
            while (self._pending_jobs_amount > 0 or futures) and self._are_jobs_cancelled is False:
                while self._job_queue and (len(futures) < max_futures):
                    package = self._job_queue.popleft()
                    assert_success = self._assert_there_are_no_cycles(package)
                    if assert_success:
                        future = thread_executor.submit(self._operate_on_next_job, package, self._notifications)
                        futures.append((package, future))

                self._handle_notifications(True)
                futures = self._remove_done_futures(futures)
                self._record_work_in_progress()
                self._check_clock()
                sys.stdout.flush()
                if self._fail_policy == JobFailPolicy.FAIL_GRACEFULLY and self._unhandled_errors:
                    self._are_jobs_cancelled = True

            if self._are_jobs_cancelled:
                self._record_jobs_cancelled([])
                self._cancel_futures(futures)

    def _execute_without_threads(self, just_one_tick: bool = False) -> None:
        while self._pending_jobs_amount > 0 and self._are_jobs_cancelled is False:
            package = self._job_queue.popleft() if self._job_queue else None
            if package is not None:
                assert_success = self._assert_there_are_no_cycles(package)
                if assert_success:
                    try:
                        self._operate_on_next_job(package, self._notifications)
                    except Exception as e:
                        self._handle_notifications(False)
                        self._handle_raised_exception(package, e)
                    else:
                        self._handle_notifications(False)

            self._record_work_in_progress()
            self._check_clock()
            if just_one_tick: return
            if self._fail_policy == JobFailPolicy.FAIL_GRACEFULLY and self._unhandled_errors:
                self._are_jobs_cancelled = True

    def _operate_on_next_job(self, package: '_JobPackage', notifications: queue.Queue[Tuple['_JobState', '_JobPackage', Optional[Exception]]]) -> None:
        if self._are_jobs_cancelled:
            notifications.put((_JobState.JOB_CANCELLED, package, None))
            return

        job, worker = package.job, package.worker
        notifications.put((_JobState.JOB_STARTED, package, None))

        jobs, error = worker.operate_on(job)

        if error is not None:
            notifications.put((_JobState.NIL, package, error))
        else:
            package.next_jobs = jobs
            notifications.put((_JobState.JOB_COMPLETED, package, None))

    def _retry_package(self, package: '_JobPackage') -> Optional['Job']:
        if self._are_jobs_cancelled:
            return None

        job: Optional[Job] = None
        tries = package.tries
        if tries < self._max_tries:
            try:
                job = package.job.retry_job()
            except Exception as e:
                self._add_unhandled_exception(e)
            tries += 1

        if job is None:
            try:
                job = package.job.backup_job()
            except Exception as e:
                self._add_unhandled_exception(e)
            tries = 0

        if job is None:
            return None

        worker = self._workers.get(job.type_id, None)
        if worker is None:
            self._add_unhandled_exception(CantPushJobs('Retry failed because there no worker is registered for the job.'), ctx='retry-package', package=package, sub_job=('retry', job))
            return None

        retry_package = _JobPackage(
            job=job,
            worker=worker,
            tries=tries,
            parent=None,
            next_jobs=package.next_jobs
        )
        if job.priority:
            self._job_queue.appendleft(retry_package)
        else:
            self._job_queue.append(retry_package)

        return job

    def _handle_notifications(self, block: bool) -> None:
        while True:
            try:
                notification = self._notifications.get(block=block, timeout=self._wait_time)
            except queue.Empty:
                break

            status, package, error = notification
            if error is not None:
                self._handle_returned_error(package, error)
            elif status == _JobState.JOB_COMPLETED:
                next_jobs = []
                if not self._are_jobs_cancelled:
                    for child_job in package.next_jobs:
                        ex = self._internal_push_job(child_job, parent_package=package)
                        if ex is not None:
                            self._add_unhandled_exception(ex, package=package, sub_job=('child', child_job), ctx='handle-notifications-push-job')
                            continue

                        next_jobs.append(child_job)

                self._record_job_completed(package, next_jobs)
            elif status == _JobState.JOB_STARTED:
                self._record_job_started(package)
            elif status == _JobState.JOB_CANCELLED:
                self._jobs_cancelled.append(package.job)
            else:
                self._add_unhandled_exception(ValueError(f'Unhandled JobState notification: {status}'), package=package, ctx='handle-notifications-switch-status')

            if block and status != _JobState.JOB_STARTED:
                break

    def _handle_returned_error(self, package: '_JobPackage', e: Exception) -> None:
        retry_job = self._retry_package(package)
        if retry_job is not None:
            self._record_job_retried(package, retry_job, e)
        else:
            self._record_job_failed(package, e)

    def _remove_done_futures(self, futures: list[Tuple['_JobPackage', Future[None]]]) -> list[Tuple['_JobPackage', Future[None]]]:
        still_pending = []
        for package, future in futures:
            if future.done():
                e = future.exception()
                if e is not None:
                    self._handle_raised_exception(package, e)
            else:
                still_pending.append((package, future))
        return still_pending

    def _cancel_futures(self, futures: list[Tuple['_JobPackage', Future[None]]]) -> None:
        for package, future in futures:
            if future.cancel():
                self._jobs_cancelled.append(package.job)
            elif (e := future.exception()) is not None:
                self._add_unhandled_exception(e, package=package, ctx='cancel-futures')
                self._record_job_failed(package, _wrap_unknown_base_error(e))

    def _handle_raised_exception(self, package: '_JobPackage', e: BaseException) -> None:
        self._add_unhandled_exception(e, package, ctx='handle-raised-exception')

        if isinstance(e, JobSystemAbortException):
            self._record_job_failed(package, e)
            return

        self._handle_returned_error(package, _wrap_unknown_base_error(e))

    def _add_unhandled_exception(self, e: BaseException, package: Optional['_JobPackage'] = None, sub_job: Optional[Tuple[str, 'Job']] = None, ctx: Optional[str] = None, method: Optional[Callable] = None) -> None:
        if self._fail_policy == JobFailPolicy.FAIL_FAST: raise e

        msg = f'WARNING! {ctx or _unknown}: '
        if isinstance(e, JobSystemAbortException):
            msg += f'Unexpected system abort '
        else:
            msg += f'Unexpected exception '

        msg += f'"{type(e).__name__}"'

        if method is not None:
            msg += f' at "{method.__qualname__}"'

        if package is not None:
            info = getattr(package.job, 'info', None)
            msg += f' while operating on job [{package.job.type_id}|{type(package.job).__name__}{f": {info}" if info else ""}] {str(package.job)}'

        if sub_job is not None:
            info = getattr(sub_job[1], 'info', None)
            msg += f' trying to spawn "{sub_job[0]}" job [{sub_job[1].type_id}|{type(sub_job[1]).__name__}{f": {info}" if info else ""}]'

        self._logger.print('ERROR: A worker failed! Please, try again later!')
        self._logger.debug(msg, e)
        self._unhandled_errors.append(e)

    def _raise_unhandled_exceptions(self, errors: List[BaseException]) -> None:
        if not errors: return

        msg = f'Unhandled exceptions: {len(errors)}\n'
        for i, e in enumerate(errors[:0:-1]):
            e_text = ''.join(traceback.TracebackException.from_exception(e).format())
            msg += f'  ({len(errors) - i}) {type(e).__name__}: {e_text}\n'

        self._logger.debug(msg)
        raise errors[0]

    def _update_timeout_clock(self) -> None:  # We only want to update the timeout when the state of the job pipeline changes
        self._timeout_clock = self._time_monotonic() + self._max_timeout

    def _check_clock(self) -> None:
        now = self._time_monotonic()

        last_progress = self._activity_tracker.last_progress_time
        if last_progress is not None and last_progress + self._max_timeout > now:
            self._update_timeout_clock()
            return

        if self._timeout_clock > now:
            return

        self._timed_out = True
        self._are_jobs_cancelled = True
        self._logger.print(f'WARNING! Jobs timeout reached after {self._max_timeout} seconds!')

    def _assert_there_are_no_cycles(self, package: '_JobPackage') -> bool:
        parent_package = package.parent
        if parent_package is None: return True

        seen: Dict[int, int] = dict()
        current: Optional[_JobPackage] = parent_package

        while current is not None:
            seen_value = seen.get(current.job.type_id, 0)
            if seen_value >= self._max_cycle:
                ex = CycleDetectedException(f'Can not use Job because it introduced a cycle of length "{seen_value}".')
                self._add_unhandled_exception(ex, package=package, ctx='assert-there-are-no-cycles')
                if package.parent is not None:
                    self._record_job_failed(package, ex)
                return False

            seen[current.job.type_id] = seen_value + 1
            current = current.parent
        
        return True

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
        self._logger.print(f"SIGNAL '{signal.strsignal(sig)}' RECEIVED!")
        try:
            for thread_name, stack in stacks_from_all_threads().items():
                msg = f"Thread: {thread_name} [{len(stack)}]\n"
                for entry in stack: msg += f"  {entry['file']}:{entry['line']} ({entry['func']})\n"
                self._logger.debug(msg)
        except Exception as _: pass
        self._logger.print('SHUTTING DOWN...')
        self._are_jobs_cancelled = True
        try:
            if callable(previous_handler) and previous_handler not in (signal.SIG_IGN, signal.SIG_DFL): previous_handler(sig, frame)
        except Exception as e:
            self._logger.print('PREVIOUS HANDLER FAILED!', sig, e)

    def _record_job_started(self, package: '_JobPackage') -> None:
        self._update_timeout_clock()
        self._try_report('report-started', self._reporter_for_package(package).notify_job_started, package.job)

    def _record_job_completed(self, package: '_JobPackage', next_jobs: List['Job']) -> None:
        self._pending_jobs_amount -= 1
        self._update_timeout_clock()
        self._try_report('report-completed', self._reporter_for_package(package).notify_job_completed, package.job, next_jobs)

    def _record_job_retried(self, package: '_JobPackage', retry_job: 'Job', e: Exception) -> None:
        self._update_timeout_clock()
        self._try_report('report-retried', self._reporter_for_package(package).notify_job_retried, package.job, retry_job, e)

    def _record_job_failed(self, package: '_JobPackage', e: Exception) -> None:
        self._pending_jobs_amount -= 1
        self._update_timeout_clock()
        self._try_report('report-failed', self._reporter_for_package(package).notify_job_failed, package.job, e)

    def _record_jobs_cancelled(self, jobs: List['Job']) -> None:
        self._update_timeout_clock()
        self._try_report('report-cancelled', self._reporter.notify_jobs_cancelled, jobs)

    def _record_work_in_progress(self) -> None: self._try_report('in-progress', self._reporter.notify_work_in_progress)

    def _try_report(self, context: str, method: Callable, *args) -> None:
        try: method(*args)
        except Exception as e: self._add_unhandled_exception(e, ctx=context, method=method)

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
    
    def backup_job(self) -> Optional['Job']:
        return None

    def add_tag(self, tag: Union[str, int]) -> 'Job':
        tags = getattr(self, '_tags', None)
        if tags is None:
            self._tags = set()
        self._tags.add(tag)
        return self

    def has_tag(self, tag: Union[str, int]) -> bool:
        tags = getattr(self, '_tags', None)
        if tags is None: return False
        return tag in tags

    @property
    def tags(self) -> Iterable[Union[str, int]]:
        return getattr(self, '_tags', set())

    @property
    def priority(self) -> bool: return False


WorkerResult = Tuple[List[Job], Optional[Exception]]

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
        """Called when pending jobs are cancelled. System must interrupt all ongoing activities."""

    def notify_job_completed(self, job: Job, next_jobs: List[Job]) -> None:
        """Called when a job is completed. Must not throw exceptions."""

    def notify_job_failed(self, job: Job, exception: Exception) -> None:
        """Called when a job fails. Must not throw exceptions."""

    def notify_job_retried(self, job: Job, retry_job: Job, exception: Exception) -> None:
        """Called when a job is retried. Must not throw exceptions."""


class JobSystemAbortException(Exception): pass
class CantRegisterWorkerException(JobSystemAbortException): pass
class CantSetSignalsException(JobSystemAbortException): pass
class CantExecuteJobs(JobSystemAbortException): pass
class CantPushJobs(JobSystemAbortException): pass
class CantWaitWhenNotExecutingJobs(JobSystemAbortException): pass
class CantWaitWhenTimedOut(JobSystemAbortException): pass
class CycleDetectedException(JobSystemAbortException): pass

class JobSystemLogger(Protocol):
    def print(self, *args, sep: str='', end: str='\n', file=sys.stdout, flush: bool=True) -> None: """Prints a message to the logger."""
    def debug(self, *args, sep: str='', end: str='\n', flush: bool=True) -> None: """Prints a debug message to the logger."""


@dataclass(eq=False, order=False)
class _JobPackage:
    __slots__ = ('job', 'worker', 'tries', 'next_jobs', 'parent')

    job: Job
    worker: Worker
    tries: int
    next_jobs: List[Job]
    parent: Optional['_JobPackage']

    # Consider removing __str__ at least in non-debug environments
    def __str__(self) -> str: return f'JobPackage(job_type_id={self.job.type_id}, job_class={self.job.__class__.__name__}, tries={self.tries})'

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

_unknown = 'unknown'

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
