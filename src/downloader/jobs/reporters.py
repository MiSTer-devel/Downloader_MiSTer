# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from collections import defaultdict
from typing import Optional, Type, TypeVar, Generic, Protocol, Union

from downloader.db_entity import DbEntity
from downloader.interruptions import Interruptions
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.path_package import PathPackage
from downloader.job_system import ProgressReporter, Job
from downloader.logger import Logger
from downloader.update_output import UpdateOutput
from types import TracebackType


class DownloaderProgressReporter(ProgressReporter):

    def __init__(self, logger: Logger, other_reporters: list[ProgressReporter]) -> None:
        self._logger = logger
        self._other_reporters = other_reporters
        self._failed_jobs: list[Job] = []

    @property
    def failed_jobs(self):
        return [*self._failed_jobs]

    def notify_job_started(self, job: Job) -> None:
        pass

    def notify_work_in_progress(self) -> None:
        for r in self._other_reporters:
            r.notify_work_in_progress()

    def notify_jobs_cancelled(self, _jobs: list[Job]) -> None:
        pass

    def notify_job_completed(self, job: Job, next_jobs: list[Job]) -> None:
        pass

    def notify_job_failed(self, job: Job, exception: BaseException) -> None:
        self._failed_jobs.append(job)
        self._logger.debug(exception)

    def notify_job_retried(self, job: Job, retry_job: Job, exception: BaseException) -> None:
        pass

@dataclasses.dataclass
class ProcessedFolder:
    pkg: PathPackage
    dbs: set[str]

TJob = TypeVar("TJob", bound=Job)
class InstallationReport(Protocol):
    def get_completed_jobs(self, type_class: Type[TJob]) -> list[TJob]: """Return all successful jobs for a job class."""
    def get_started_jobs(self, type_class: Type[TJob]) -> list[TJob]: """Return all started jobs for a job class."""
    def get_failed_jobs(self, type_class: Type[TJob]) ->  list[tuple[TJob, BaseException]]: """Return all failed jobs for a job class."""
    def get_retried_jobs    (self, job_class: Type[TJob]) -> list[tuple[TJob, BaseException]]: """Return all retried jobs for a job class."""
    def get_cancelled_jobs  (self, job_class: Type[TJob]) -> list[TJob]: """Return all cancelled jobs for a job class."""
    def processed_folder(self, path: str) -> dict[str, PathPackage]: """File that a database is currently processing."""
    def all_processed_folders(self) -> list[str]: """Returns all processed folders."""
    def get_jobs_completed_by_tag(self, tag: str) -> list[Job]: """Returns all jobs completed by a tag."""
    def get_jobs_failed_by_tag(self, tag: str) -> list[Job]: """Returns all jobs failed by a tag."""


class JobTagTracking:
    # To avoid errors, the jobs passed here need to be kept alive in memory, since we are using their address as key,
    # and a new job with the same address of an old one would cause very hard to debug problems.
    def __init__(self) -> None:
        self.in_progress: dict[Union[str, int], set[int]] = defaultdict(set)
        self._initiated: set[int] = set()
        self._ended: set[int] = set()

    def reset(self) -> None:
        self.in_progress.clear()
        self._initiated.clear()
        self._ended.clear()

    def add_job_started(self, job: Job) -> None:
        self._add_job_in_progress(job)

    def add_jobs_cancelled(self, jobs: list[Job]) -> None:
        for job in jobs:
            self._remove_job_in_progress(job)

    def add_job_completed(self, job: Job, next_jobs: list[Job]) -> None:
        auto_spawn = False
        for c_job in next_jobs:
            if c_job == job:
                auto_spawn = True
                continue
            self._reset_lifecycle(c_job)
            self._add_job_in_progress(c_job)

        if not auto_spawn:
            self._remove_job_in_progress(job)

    def add_job_failed(self, job: Job) -> None:
        self._remove_job_in_progress(job)

    def add_job_retried(self, job: Job, retry_job: Job) -> None:
        if job != retry_job:
            self._reset_lifecycle(retry_job)
            self._add_job_in_progress(retry_job)
            self._remove_job_in_progress(job)

    def _add_job_in_progress(self, job: Job) -> None:
        job_id = id(job)
        if job_id not in self._initiated:
            self._initiated.add(job_id)
        if job_id in self._ended:
            return
        
        for tag in job.tags:
            self.in_progress[tag].add(job_id)

    def _remove_job_in_progress(self, job: Job) -> None:
        job_id = id(job)
        if job_id not in self._ended:
            self._ended.add(job_id)
        if job_id not in self._initiated:
            return

        for tag in job.tags:
            self.in_progress[tag].discard(job_id)

    def _reset_lifecycle(self, job: Job) -> None:
        job_id = id(job)
        self._initiated.discard(job_id)
        self._ended.discard(job_id)

T = TypeVar('T')
class _WithLock(Generic[T]):
    __slots__ = ("data", "lock")
    def __init__(self, data: T, lock: Optional[threading.Lock] = None) -> None:
        self.data = data
        self.lock = lock or threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        return self.data

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> None:
        self.lock.release()


class InstallationReportImpl(InstallationReport):
    def __init__(self) -> None:
        # These are only accessed in the main thread
        self._jobs_started: dict[int, list[Job]] = defaultdict(list)
        self._jobs_completed: dict[int, list[Job]] = defaultdict(list)
        self._jobs_cancelled: dict[int, list[Job]] = defaultdict(list)
        self._jobs_failed: dict[int, list[tuple[Job, BaseException]]] = defaultdict(list)
        self._jobs_retried: dict[int, list[tuple[Job, BaseException]]] = defaultdict(list)

        # Following might be modified by multiple threads, but read only in the main thread
        self._processed_files_set = _WithLock[set[str]](set())
        self._processed_folders = _WithLock[dict[str, dict[str, PathPackage]]]({})
        self._processed_folders_set = _WithLock[set[str]](set())
        job_tag_lock = threading.Lock()
        self._jobs_tag_tracking = _WithLock[JobTagTracking](JobTagTracking(), job_tag_lock)

        # Following might be modified and read in multiple threads
        self._jobs_tag_completed = _WithLock[dict[Union[str, int], list[Job]]](defaultdict(list), job_tag_lock)
        self._jobs_tag_failed = _WithLock[dict[Union[str, int], list[Job]]](defaultdict(list), job_tag_lock)

    def add_job_started(self, job: Job) -> None:
        self._jobs_started[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking: tracking.add_job_started(job)

    def add_jobs_cancelled(self, jobs: list[Job]) -> None:
        for job in jobs: self._jobs_cancelled[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking: tracking.add_jobs_cancelled(jobs)

    def add_job_completed(self, job: Job, next_jobs: list[Job]) -> None:
        self._jobs_completed[job.type_id].append(job)
        with self._jobs_tag_tracking as tracking:
            tracking.add_job_completed(job, next_jobs)
            for tag in job.tags:
                self._jobs_tag_completed.data[tag].append(job)

    def add_job_failed(self, job: Job, exception: BaseException) -> None:
        self._jobs_failed[job.type_id].append((job, exception))
        with self._jobs_tag_tracking as tracking:
            tracking.add_job_failed(job)
            for tag in job.tags:
                self._jobs_tag_failed.data[tag].append(job)

    def add_job_retried(self, job: Job, retry_job: Job, exception: BaseException) -> None:
        self._jobs_retried[job.type_id].append((job, exception))
        with self._jobs_tag_tracking as tracking: tracking.add_job_retried(job, retry_job)

    def any_in_progress_job_with_tags(self, tags: list[str]) -> bool:
        if len(tags) == 0: return False
        with self._jobs_tag_tracking as tracking:
            for tag in tags:
                if len(tracking.in_progress[tag]) > 0: return True

        return False

    def get_jobs_completed_by_tag(self, tag: str) -> list[Job]:
        with self._jobs_tag_completed as tag_completed:
            return tag_completed[tag]

    def get_jobs_failed_by_tag(self, tag: str) -> list[Job]:
        with self._jobs_tag_failed as tag_failed:
            return tag_failed[tag]

    def add_processed_files(self, files: list[PathPackage]) -> tuple[list[PathPackage], list[str]]:
        if len(files) == 0: return [], []

        files_set = {pkg.rel_path for pkg in files}
        with self._processed_files_set as processed_files_set:
            duplicates = files_set.intersection(processed_files_set)
            processed_files_set.update(files_set)

        non_duplicates_set = files_set - duplicates
        non_duplicates = [pkg for pkg in files if pkg.rel_path in non_duplicates_set]

        return non_duplicates, list(duplicates)

    def add_processed_folders(self, folders: list[PathPackage], db_id: str) -> list[PathPackage]:
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

    def get_started_jobs    (self, job_class: Type[TJob]) -> list[TJob]:                        return self._jobs_started   [job_class.type_id]  # type: ignore[return-value, index]
    def get_completed_jobs  (self, job_class: Type[TJob]) -> list[TJob]:                        return self._jobs_completed [job_class.type_id]  # type: ignore[return-value, index]
    def get_failed_jobs     (self, job_class: Type[TJob]) -> list[tuple[TJob, BaseException]]:  return self._jobs_failed    [job_class.type_id]  # type: ignore[return-value, index]
    def get_retried_jobs    (self, job_class: Type[TJob]) -> list[tuple[TJob, BaseException]]:  return self._jobs_retried   [job_class.type_id]  # type: ignore[return-value, index]
    def get_cancelled_jobs  (self, job_class: Type[TJob]) -> list[TJob]:                        return self._jobs_cancelled [job_class.type_id]  # type: ignore[return-value, index]

    # All the rest are Non-thread-safe: Should only be used after threads are out
    def processed_folder(self, path: str) -> dict[str, PathPackage]: return self._processed_folders.data[path]
    def all_processed_folders(self) -> list[str]: return list(self._processed_folders.data.keys())


class FileDownloadSessionLogger(Protocol):
    def print_progress_line(self, line: str) -> None:
        """Prints a progress line."""

    def print_pending(self) -> None:
        """Prints pending progress."""

    def print_header(self, db: DbEntity) -> None:
        """Prints a header."""


class FileDownloadProgressReporter(ProgressReporter, FileDownloadSessionLogger):
    def __init__(self, logger: Logger, interrupts: Interruptions, update_output: UpdateOutput) -> None:
        self._logger = logger
        self._interrupts = interrupts
        self._update_output = update_output
        self._report: InstallationReportImpl = InstallationReportImpl()

    def installation_report(self) -> InstallationReport: return self._report
    def session_logger(self) -> FileDownloadSessionLogger: return self

    def set_installation_report(self, report: InstallationReportImpl):
        self._report = report

    def notify_job_started(self, job: Job) -> None:
        self._report.add_job_started(job)
        if isinstance(job, FetchFileJob) and job.db_id is not None:
            self._update_output.file_started(job.db_id, job.pkg.rel_path, job.pkg.description['size'], job.already_exists)
        if isinstance(job, FetchDataJob):
            self._logger.bench('FileDownloadProgressReporter FetchDataJob started: ', job.source)

    def notify_work_in_progress(self) -> None:
        self._update_output.work_in_progress()

    def notify_job_completed(self, job: Job, next_jobs: list[Job]) -> None:
        self._report.add_job_completed(job, next_jobs)
        if isinstance(job, FetchFileJob) and job.db_id is not None:
            self._update_output.file_completed(job.db_id, job.pkg.rel_path, job.pkg.description['size'])
        if isinstance(job, OpenZipContentsJob):
            for pkg in job.validated_files:
                self._update_output.file_completed(job.db.db_id, pkg.rel_path, pkg.description['size'], job.zip_id)
        if isinstance(job, FetchDataJob):
            self._logger.bench('FileDownloadProgressReporter FetchDataJob completed: ', job.source)

    def notify_job_failed(self, job: Job, exception: BaseException) -> None:
        self._report.add_job_failed(job, exception)
        if isinstance(job, FetchFileJob) and job.db_id is not None:
            self._update_output.file_failed(job.db_id, job.pkg.rel_path, job.pkg.description['size'], type(exception).__name__)
        if isinstance(job, OpenZipContentsJob):
            for pkg in job.files_to_unzip:
                self._update_output.file_failed(job.db.db_id, pkg.rel_path, pkg.description['size'], type(exception).__name__)
        if isinstance(job, FetchFileJob) and job.db_id is not None:
            self._logger.debug(exception)

    def notify_job_retried(self, job: Job, retry_job: Job, exception: BaseException) -> None:
        self._report.add_job_retried(job, retry_job, exception)
        if isinstance(job, FetchFileJob) and job.db_id is not None:
            self._logger.debug(exception)

    def notify_jobs_cancelled(self, jobs: list[Job]) -> None:
        self._report.add_jobs_cancelled(jobs)
        self._update_output.jobs_cancelled(len(jobs))
        try:
            self._interrupts.interrupt()
        except Exception as e:
            self._logger.debug(e)

    def print_progress_line(self, line: str) -> None: self._update_output.progress_line(line)
    def print_pending(self) -> None: self._update_output.flush_pending()
    def print_header(self, db: DbEntity) -> None:  self._update_output.database_started(db.db_id)
