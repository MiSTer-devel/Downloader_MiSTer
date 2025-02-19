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

import dataclasses
import threading
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple, List, Set, Type, TypeVar, Generic, Protocol, Union

from downloader.db_entity import DbEntity
from downloader.interruptions import Interruptions
from downloader.jobs.get_file_job import GetFileJob
from downloader.path_package import PathPackage
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.waiter import Waiter
from downloader.job_system import ProgressReporter, Job
from downloader.logger import Logger


class DownloaderProgressReporter(ProgressReporter):

    def __init__(self, logger: Logger, other_reporters: List[ProgressReporter]):
        self._logger = logger
        self._other_reporters = other_reporters
        self._failed_jobs: List[Job] = []

    @property
    def failed_jobs(self):
        return [*self._failed_jobs]

    def notify_job_started(self, job: Job):
        pass

    def notify_work_in_progress(self):
        for r in self._other_reporters:
            r.notify_work_in_progress()

    def notify_jobs_cancelled(self, _jobs: List[Job]) -> None:
        pass

    def notify_job_completed(self, job: Job, next_jobs: List[Job]):
        pass

    def notify_job_failed(self, job: Job, exception: BaseException):
        self._failed_jobs.append(job)
        self._logger.debug(exception)

    def notify_job_retried(self, job: Job, retry_job: Job, exception: BaseException):
        pass


class ProcessedFile:
    __slots__ = ('pkg', 'db_id')
    def __init__(self, pkg: PathPackage, db_id: str,/):
        self.pkg = pkg
        self.db_id = db_id


@dataclasses.dataclass
class ProcessedFolder:
    pkg: PathPackage
    dbs: Set[str]

TJob = TypeVar("TJob", bound=Job)
class InstallationReport(Protocol):
    def get_completed_jobs(self, type_class: Type[TJob]) -> List[TJob]: """Return all successful jobs for a job class."""
    def get_started_jobs(self, type_class: Type[TJob]) -> List[TJob]: """Return all started jobs for a job class."""
    def get_failed_jobs(self, type_class: Type[TJob]) ->  List[Tuple[TJob, BaseException]]: """Return all failed jobs for a job class."""
    def get_retried_jobs    (self, job_class: Type[TJob]) -> List[Tuple[TJob, BaseException]]: """Return all retried jobs for a job class."""
    def get_cancelled_jobs  (self, job_class: Type[TJob]) -> List[TJob]: """Return all cancelled jobs for a job class."""
    def processed_folder(self, path: str) -> Dict[str, PathPackage]: """File that a database is currently processing."""
    def all_processed_folders(self) -> List[str]: """Returns all processed folders."""
    def get_jobs_completed_by_tag(self, tag: str) -> List[Job]: """Returns all jobs completed by a tag."""
    def get_jobs_failed_by_tag(self, tag: str) -> List[Job]: """Returns all jobs failed by a tag."""


class JobTagTracking:
    # To avoid errors, the jobs passed here need to be kept alive in memory, since we are using their address as key,
    # and a new job with the same address of an old one would cause very hard to debug problems.
    def __init__(self):
        self.in_progress: Dict[Union[str, int], Set[int]] = defaultdict(set)
        self._initiated: Set[int] = set()
        self._ended: Set[int] = set()

    def add_job_started(self, job: Job):
        self._add_job_in_progress(job)

    def add_jobs_cancelled(self, jobs: List[Job]) -> None:
        for job in jobs:
            self._remove_job_in_progress(job)

    def add_job_completed(self, job: Job, next_jobs: List[Job]):
        auto_spawn = False
        for c_job in next_jobs:
            if c_job == job:
                auto_spawn = True
                continue
            self._reset_lifecycle(c_job)
            self._add_job_in_progress(c_job)

        if not auto_spawn:
            self._remove_job_in_progress(job)

    def add_job_failed(self, job: Job):
        self._remove_job_in_progress(job)

    def add_job_retried(self, job: Job, retry_job: Job):
        if job != retry_job:
            self._reset_lifecycle(retry_job)
            self._add_job_in_progress(retry_job)
            self._remove_job_in_progress(job)

    def _add_job_in_progress(self, job: Job):
        job_id = id(job)
        if job_id not in self._initiated:
            self._initiated.add(job_id)
        if job_id in self._ended:
            return
        
        for tag in job.tags:
            self.in_progress[tag].add(job_id)

    def _remove_job_in_progress(self, job: Job):
        job_id = id(job)
        if job_id not in self._ended:
            self._ended.add(job_id)
        if job_id not in self._initiated:
            return

        for tag in job.tags:
            if job_id not in self.in_progress[tag]:
                continue
            self.in_progress[tag].remove(job_id)

    def _reset_lifecycle(self, job: Job):
        job_id = id(job)
        if job_id in self._initiated: self._initiated.remove(job_id)
        if job_id in self._ended: self._ended.remove(job_id)

T = TypeVar('T')
class _WithLock(Generic[T]):
    __slots__ = ("data", "lock")
    def __init__(self, data: T, lock: Optional[threading.Lock] = None):
        self.data = data
        self.lock = lock or threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        return self.data

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class InstallationReportImpl(InstallationReport):
    def __init__(self):
        # These are only accessed in the main thread
        self._jobs_started: Dict[int, List[Job]] = defaultdict(list)
        self._jobs_completed: Dict[int, List[Job]] = defaultdict(list)
        self._jobs_cancelled: Dict[int, List[Job]] = defaultdict(list)
        self._jobs_failed: Dict[int, List[Tuple[Job, BaseException]]] = defaultdict(list)
        self._jobs_retried: Dict[int, List[Tuple[Job, BaseException]]] = defaultdict(list)

        # Following might be modified by multiple threads, but read only in the main thread
        self._processed_files_set = _WithLock[Set[str]](set())
        self._processed_folders = _WithLock[Dict[str, Dict[str, PathPackage]]]({})
        self._processed_folders_set = _WithLock[Set[str]](set())
        job_tag_lock = threading.Lock()
        self._jobs_tag_tracking = _WithLock[JobTagTracking](JobTagTracking(), job_tag_lock)

        # Following might be modified and read in multiple threads
        self._jobs_tag_completed = _WithLock[Dict[Union[str, int], List[Job]]](defaultdict(list), job_tag_lock)
        self._jobs_tag_failed = _WithLock[Dict[Union[str, int], List[Job]]](defaultdict(list), job_tag_lock)

    def add_job_started(self, job: Job):
        self._jobs_started[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking: tracking.add_job_started(job)

    def add_jobs_cancelled(self, jobs: List[Job]) -> None:
        for job in jobs: self._jobs_cancelled[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking: tracking.add_jobs_cancelled(jobs)

    def add_job_completed(self, job: Job, next_jobs: List[Job]):
        self._jobs_completed[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking:
            tracking.add_job_completed(job, next_jobs)
            for tag in job.tags:
                self._jobs_tag_completed.data[tag].append(job)

    def add_job_failed(self, job: Job, exception: BaseException):
        self._jobs_failed[job.type_id].append((job, exception))
        with self._jobs_tag_tracking as tracking:
            tracking.add_job_failed(job)
            for tag in job.tags:
                self._jobs_tag_failed.data[tag].append(job)

    def add_job_retried(self, job: Job, retry_job: Job, exception: BaseException):
        self._jobs_retried[job.type_id].append((job, exception))
        with self._jobs_tag_tracking as tracking: tracking.add_job_retried(job, retry_job)

    def any_in_progress_job_with_tags(self, tags: List[str]) -> bool:
        if len(tags) == 0: return False
        with self._jobs_tag_tracking as tracking:
            for tag in tags:
                if len(tracking.in_progress[tag]) > 0: return True

        return False

    def get_jobs_completed_by_tag(self, tag: str) -> List[Job]:
        with self._jobs_tag_completed as tag_completed:
            return tag_completed[tag]

    def get_jobs_failed_by_tag(self, tag: str) -> List[Job]:
        with self._jobs_tag_failed as tag_failed:
            return tag_failed[tag]

    def add_processed_files(self, files: List[PathPackage]) -> Tuple[List[PathPackage], List[str]]:
        if len(files) == 0: return [], []

        files_set = {pkg.rel_path for pkg in files}
        with self._processed_files_set as processed_files_set:
            duplicates = files_set.intersection(processed_files_set)
            processed_files_set.update(files_set)

        non_duplicates_set = files_set - duplicates
        non_duplicates = [pkg for pkg in files if pkg.rel_path in non_duplicates_set]

        return non_duplicates, list(duplicates)

    def add_processed_folders(self, folders: List[PathPackage], db_id: str) -> List[PathPackage]:
        if len(folders) == 0: return []
        non_already_present = []
        with self._processed_folders as processed_folders:
            for pkg in folders:
                if pkg.rel_path in processed_folders:
                    if db_id in processed_folders[pkg.rel_path]:
                        processed_folders[pkg.rel_path][db_id].description.update(pkg.description)
                    else:
                        processed_folders[pkg.rel_path][db_id] = pkg
                else:
                    non_already_present.append(pkg)
                    processed_folders[pkg.rel_path] = {db_id: pkg}

        return non_already_present

    def get_started_jobs    (self, job_class: Type[TJob]) -> List[TJob]:                        return self._jobs_started   [job_class.type_id]
    def get_completed_jobs  (self, job_class: Type[TJob]) -> List[TJob]:                        return self._jobs_completed [job_class.type_id]
    def get_failed_jobs     (self, job_class: Type[TJob]) -> List[Tuple[TJob, BaseException]]:  return self._jobs_failed    [job_class.type_id]
    def get_retried_jobs    (self, job_class: Type[TJob]) -> List[Tuple[TJob, BaseException]]:  return self._jobs_retried   [job_class.type_id]
    def get_cancelled_jobs  (self, job_class: Type[TJob]) -> List[TJob]:                        return self._jobs_cancelled [job_class.type_id]

    # All the rest are Non-thread-safe: Should only be used after threads are out
    def processed_folder(self, path: str) -> Dict[str, PathPackage]: return self._processed_folders.data[path]
    def all_processed_folders(self) -> List[str]: return list(self._processed_folders.data.keys())


class FileDownloadSessionLogger(Protocol):
    def start_session(self):
        '''Starts a new session.'''

    def print_progress_line(self, line: str):
        '''Prints a progress line.'''

    def print_pending(self):
        '''Prints pending progress.'''

    def print_header(self, db: DbEntity):
        '''Prints a header.'''

    def report(self) -> InstallationReport:
        '''Returns the report.'''


class FileDownloadSessionLoggerImpl(FileDownloadSessionLogger):

    def __init__(self, logger: Logger, waiter: Waiter):
        self._logger = logger
        self._waiter = waiter
        self._check_time: float = 0
        self._deactivated: bool = False
        self._needs_newline: bool = False
        self._need_clear_header: bool = False
        self._symbols: List[str] = []

    def start_session(self):
        self.__init__(self._logger, self._waiter)

    def _deactivate(self):
        self._deactivated = True

    def print_job_started(self, job: Job):
        if isinstance(job, GetFileJob) and not job.silent:
            self._print_line(job.info)

        self._check_time = time.time() + 2.0

    def print_work_in_progress(self):
        if self._deactivated:
            return
        now = time.time()
        if self._check_time < now:
            self._symbols.append('*')
            self._print_symbols()

    def print_jobs_cancelled(self, jobs: List[Job]) -> None:
        self._logger.print(f"Cancelled {len(jobs)} jobs.")

    def print_job_completed(self, job: Job, _next_jobs: List[Job]):
        if isinstance(job, GetFileJob) and not job.silent:
            self._symbols.append('.')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

        elif isinstance(job, ValidateFileJob) and job.after_job is None:
            self._symbols.append('+')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

    def _print_symbols(self):
        if len(self._symbols) == 0:
            return

        last_is_asterisk = self._symbols[-1] == '*'

        self._logger.print(('\n' if self._need_clear_header else '') + ''.join(self._symbols), end='')
        self._symbols.clear()

        self._need_clear_header = False
        self._needs_newline = True
        self._check_time = time.time() + (1.0 if last_is_asterisk else 2.0)

    def _print_line(self, line):
        if self._need_clear_header: line = '\n' + line
        if self._needs_newline: line = '\n' + line
        self._logger.print(line)
        self._needs_newline = False
        self._need_clear_header = False

    def print_progress_line(self, line):
        self._print_line(line)
        self._check_time = time.time() + 2.0

    def print_pending(self):
        self._print_symbols()
        if self._needs_newline:
            self._logger.print()
            self._needs_newline = False

    def print_header(self, db: DbEntity):
        self._print_symbols()
        first_line = '\n' if self._needs_newline else ''
        self._needs_newline = False
        if len(db.header):
            count_float = 0
            for line in db.header:
                if isinstance(line, float):
                    count_float += 1
            if count_float > 100:
                self._deactivate()

            text = first_line + \
                '################################################################################\n'

            for line in db.header:
                if isinstance(line, float):
                    if len(text) > 0:
                        self._logger.print(text)
                        text = ''
                    self._waiter.sleep(line)
                else:
                    text += line

            if len(text) > 0: self._logger.print(text)

        else:
            self._logger.print(
                first_line +
                '################################################################################\n' +
                f'SECTION: {db.db_id}\n'
            )

        self._need_clear_header = True
        self._check_time = time.time() + 2.0

    def print_job_failed(self, job: Job, exception: BaseException):
        self._print_job_error(job, exception)

    def print_job_retried(self, job: Job, _retry_job: Job, exception: BaseException):
        self._print_job_error(job, exception)

    def _print_job_error(self, job: Job, exception: BaseException):
        if (isinstance(job, GetFileJob) and not job.silent) or isinstance(job, ValidateFileJob):
            self._logger.debug(exception)
            self._symbols.append('~')
            self._print_symbols()


class FileDownloadProgressReporter(ProgressReporter, FileDownloadSessionLogger):
    def __init__(self, logger: Logger, waiter: Waiter, interrupts: Interruptions, report: InstallationReportImpl):
        self._logger = logger
        self._interrupts = interrupts
        self._report = report
        self._session_logger = FileDownloadSessionLoggerImpl(logger, waiter)

    def session_logger(self) -> FileDownloadSessionLogger:
        return self._session_logger

    def report(self) -> InstallationReport:
        return self._report

    def notify_job_started(self, job: Job):
        self._report.add_job_started(job)
        self._session_logger.print_job_started(job)

    def notify_work_in_progress(self):
        self._session_logger.print_work_in_progress()

    def notify_job_completed(self, job: Job, next_jobs: List[Job]):
        self._report.add_job_completed(job, next_jobs)
        self._session_logger.print_job_completed(job, next_jobs)

    def notify_job_failed(self, job: Job, exception: BaseException):
        self._report.add_job_failed(job, exception)
        self._session_logger.print_job_failed(job, exception)

    def notify_job_retried(self, job: Job, retry_job: Job, exception: BaseException):
        self._report.add_job_retried(job, retry_job, exception)
        self._session_logger.print_job_retried(job, retry_job, exception)

    def notify_jobs_cancelled(self, jobs: List[Job]) -> None:
        self._report.add_jobs_cancelled(jobs)
        self._session_logger.print_jobs_cancelled(jobs)
        try:
            self._interrupts.interrupt()
        except Exception as e:
            self._logger.debug(e)

    def start_session(self): self._session_logger.start_session()
    def print_progress_line(self, line: str): self._session_logger.print_progress_line(line)
    def print_pending(self): self._session_logger.print_pending()
    def print_header(self, db: DbEntity):  self._session_logger.print_header(db)
