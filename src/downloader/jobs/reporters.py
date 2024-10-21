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

import abc
import dataclasses
import time
from typing import Dict, Optional, Tuple, List, Any, Iterable, Set

from downloader.db_entity import DbEntity
from downloader.file_filter import BadFileFilterPartException, FileFoldersHolder
from downloader.jobs.get_file_job import GetFileJob
from downloader.jobs.index import Index
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.local_store_wrapper import StoreFragmentDrivePaths
from downloader.path_package import PathPackage, PathType
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.online_importer import WrongDatabaseOptions
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

    def notify_job_completed(self, job: Job):
        pass

    def notify_job_failed(self, job: Job, exception: BaseException):
        self._failed_jobs.append(job)
        self._logger.debug(exception)

    def notify_job_retried(self, job: Job, exception: BaseException):
        pass


@dataclasses.dataclass
class ProcessedFile:
    pkg: PathPackage
    db_id: str


@dataclasses.dataclass
class ProcessedFolder:
    pkg: PathPackage
    dbs: Set[str]


class InstallationReport(abc.ABC):
    def is_file_processed(self, path: str) -> bool: """Returns True if the file has been processed."""
    def is_folder_installed(self, path: str) -> bool: """Returns True if the file has been processed."""
    def processed_file(self, path: str) -> ProcessedFile: """File that a database is currently processing."""
    def processed_folder(self, path: str) -> Dict[str, PathPackage]: """File that a database is currently processing."""
    def downloaded_files(self) -> List[str]: """Files that has just been downloaded and validated."""
    def present_not_validated_files(self) -> List[str]: """File previously in the system, that were in the store, and have NOT been validated."""
    def present_validated_files(self) -> List[str]: """File previously in the system, that were NOT in the store, and now have been validated."""
    def fetch_started_files(self) -> List[str]: """Files that have been queued for download."""
    def failed_files(self) -> List[str]: """Files that couldn't be downloaded properly or didn't pass validation."""
    def removed_files(self) -> List[str]: """Files that have just been removed."""
    def removed_copies(self) -> List[Tuple[bool, str, str]]: """Files that were copies and were removed."""
    def installed_files(self) -> List[str]: """Files that have just been installed and need to be updated in the store."""
    def installed_folders(self) -> List[str]: """Folders that have just been installed and need to be updated in the store."""
    def uninstalled_files(self) -> List[str]: """Files that have just been uninstalled for various reasons and need to be removed from the store."""
    def wrong_db_options(self) -> List[WrongDatabaseOptions]: """Databases that have been unprocessed because of their database."""
    def installed_zip_indexes(self) -> Iterable[Tuple[str, str, StoreFragmentDrivePaths, Dict[str, Any]]]: """Zip indexes that have been installed and need to be updated in the store."""
    def skipped_updated_files(self) -> List[str]: """File with an available update that didn't get updated because it has override false in its file description."""
    def filtered_zip_data(self) -> Dict[str, Any]: """Filtered zip data that has been processed."""


class InstallationReportImpl(InstallationReport):
    def __init__(self):
        self._downloaded_files = []
        self._validated_files = []
        self._present_validated_files = []
        self._present_not_validated_files = []
        self._fetch_started_files = []
        self._failed_files = []
        self._failed_db_options: List[WrongDatabaseOptions] = []
        self._removed_files = []
        self._removed_copies: List[Tuple[bool, str, str, PathType]] = []
        self._skipped_updated_files = []
        self._processed_files: Dict[str, ProcessedFile] = {}
        self._processed_folders: Dict[str, Dict[str, PathPackage]] = {}
        self._installed_zip_indexes: List[Tuple[str, str, StoreFragmentDrivePaths, Dict[str, Any]]] = []
        self._installed_folders: Set[str] = set()
        self._filtered_zip_data: List[Tuple[str, str, Dict[str, Any], Dict[str, Any]]] = []

    def add_downloaded_file(self, path: str): self._downloaded_files.append(path)
    def add_validated_file(self, path: str): self._validated_files.append(path)
    def add_installed_zip_index(self, db_id: str, zip_id: str, fragment: StoreFragmentDrivePaths, description: Dict[str, Any]): self._installed_zip_indexes.append((db_id, zip_id, fragment, description))
    def add_present_validated_files(self, paths: List[str]): self._present_validated_files.extend(paths)
    def add_present_not_validated_files(self, paths: List[str]): self._present_not_validated_files.extend(paths)
    def add_skipped_updated_files(self, paths: List[str]): self._skipped_updated_files.extend(paths)
    def add_file_fetch_started(self, path: str): self._fetch_started_files.append(path)
    def add_failed_file(self, path: str): self._failed_files.append(path)

    def add_filtered_zip_data(self, db_id: str, zip_id: str, filtered_data: FileFoldersHolder) -> None:
        files, folders = filtered_data['files'], filtered_data['folders']
        #if len(files) == 0 and len(folders) == 0: return
        self._filtered_zip_data.append((db_id, zip_id, files, folders))

    def add_failed_db_options(self, exception: WrongDatabaseOptions): self._failed_db_options.append(exception)
    def add_removed_file(self, path: str): self._removed_files.append(path)
    def add_removed_copies(self, copies: List[Tuple[bool, str, str, PathType]]): self._removed_copies.extend(copies)
    def add_installed_folder(self, path: str): self._installed_folders.add(path)
    def is_file_processed(self, path: str) -> bool: return path in self._processed_files
    def is_folder_installed(self, path: str) -> bool: return path in self._installed_folders
    def add_processed_file(self, pkg: PathPackage, db_id: str): self._processed_files[pkg.rel_path] = ProcessedFile(pkg, db_id)
    def add_processed_folder(self, pkg: PathPackage, db_id: str): self._processed_folders.setdefault(pkg.rel_path, dict())[db_id] = pkg
    def processed_file(self, path: str) -> ProcessedFile: return self._processed_files[path]
    def processed_folder(self, path: str) -> Dict[str, PathPackage]: return self._processed_folders[path]
    def downloaded_files(self): return self._downloaded_files
    def present_validated_files(self): return self._present_validated_files
    def present_not_validated_files(self): return self._present_not_validated_files
    def fetch_started_files(self): return self._fetch_started_files
    def failed_files(self): return self._failed_files
    def removed_files(self): return self._removed_files
    def removed_copies(self): return self._removed_copies
    def installed_files(self): return list(set(self._present_validated_files) | set(self._validated_files))
    def installed_folders(self): return list(self._installed_folders)
    def uninstalled_files(self): return self._removed_files + self._failed_files
    def wrong_db_options(self): return self._failed_db_options
    def installed_zip_indexes(self): return self._installed_zip_indexes
    def skipped_updated_files(self): return self._skipped_updated_files
    def filtered_zip_data(self): return self._filtered_zip_data


class FileDownloadSessionLogger:
    @abc.abstractmethod
    def start_session(self):
        '''Starts a new session.'''

    @abc.abstractmethod
    def print_progress_line(self, line):
        '''Prints a progress line.'''

    @abc.abstractmethod
    def print_pending(self):
        '''Prints pending progress.'''

    @abc.abstractmethod
    def print_header(self, db: DbEntity, nothing_to_download: bool = False):
        '''Prints a header.'''

    @abc.abstractmethod
    def report(self) -> InstallationReport:
        '''Returns the report.'''


class FileDownloadProgressReporter(ProgressReporter, FileDownloadSessionLogger):

    def __init__(self, logger: Logger, waiter: Waiter, report: InstallationReportImpl):
        self._logger = logger
        self._waiter = waiter
        self._report = report
        self._check_time: float = 0
        self._active_jobs: Dict[int, int] = {}
        self._deactivated: bool = False
        self._needs_newline: bool = False
        self._need_clear_header: bool = False
        self._symbols: List[str] = []

    def start_session(self):
        self.__init__(self._logger, self._waiter, InstallationReportImpl())

    def _deactivate(self):
        self._deactivated = True

    def report(self) -> InstallationReport:
        return self._report

    def notify_job_started(self, job: Job):
        if isinstance(job, FetchFileJob):
            self._print_line(job.path)
            self._report.add_file_fetch_started(job.path)
        if isinstance(job, GetFileJob) and not job.silent:
            self._print_line(job.info)
            self._report.add_file_fetch_started(job.info)

        self._active_jobs[job.type_id] = self._active_jobs.get(job.type_id, 0) + 1
        self._check_time = time.time() + 2.0

    def notify_work_in_progress(self):
        if self._deactivated:
            return
        now = time.time()
        if self._check_time < now:
            self._symbols.append('*')
            self._print_symbols()

    def notify_job_completed(self, job: Job):
        if isinstance(job, FetchFileJob) or (isinstance(job, GetFileJob) and not job.silent):
            self._symbols.append('.')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

            if isinstance(job, GetFileJob) and not job.silent:
                self._report.add_downloaded_file(job.info)

        elif isinstance(job, ValidateFileJob):
            self._symbols.append('+')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

            self._report.add_downloaded_file(job.fetch_job.path)
        elif isinstance(job, ValidateFileJob2) and job.after_job is None:
            self._symbols.append('+')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

            self._report.add_validated_file(job.info)

        elif isinstance(job, ProcessZipJob) and job.has_new_zip_index:
            self._report.add_installed_zip_index(job.db.db_id, job.zip_id, job.result_zip_index, job.zip_description)

        elif isinstance(job, OpenZipContentsJob):
            for file in job.downloaded_files:
                self._report.add_downloaded_file(file)
                self._report.add_validated_file(file)
            for file in job.failed_files:
                self._report.add_failed_file(file)

            self._report.add_filtered_zip_data(job.db.db_id, job.zip_id, job.filtered_data)

        self._remove_in_progress(job)

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

    def print_header(self, db: DbEntity, nothing_to_download: bool = False):
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

            text = first_line + '\n' + \
                '################################################################################\n'

            for line in db.header:
                if isinstance(line, float):
                    if len(text) > 0:
                        self._logger.print(text)
                        text = ''
                    self._waiter.sleep(line)
                else:
                    text += line

            if nothing_to_download: text += "\n\nNothing new to download from given sources."
            if len(text) > 0: self._logger.print(text)

        else:
            self._logger.print(
                first_line +
                '\n' +
                '################################################################################\n' +
                f'SECTION: {db.db_id}' +
                ("\n\nNothing new to download from given sources." if nothing_to_download else '')
            )

        self._need_clear_header = True
        self._check_time = time.time() + 2.0

    def notify_job_failed(self, job: Job, exception: BaseException):
        if isinstance(job, ProcessIndexJob) and isinstance(exception, BadFileFilterPartException):
            self._report.add_failed_db_options(
                WrongDatabaseOptions(f"Wrong custom download filter on database {job.db.db_id}. Part '{str(exception)}' is invalid.")
            )
        path = self._file_path_from_job(job)
        if path is not None:
            self._report.add_failed_file(path)
        self.notify_job_retried(job, exception)

    def notify_job_retried(self, job: Job, exception: BaseException):
        self._logger.debug(exception)
        self._symbols.append('~')
        self._print_symbols()
        self._remove_in_progress(job)

    def _file_path_from_job(self, job: Job) -> Optional[str]:
        if isinstance(job, ValidateFileJob):
            job = job.fetch_job
        elif isinstance(job, ValidateFileJob2):
            job = job.get_file_job
        if isinstance(job, FetchFileJob):
            return job.path
        elif isinstance(job, GetFileJob):
            return job.info
        else:
            return None

    def _remove_in_progress(self, job: Job):
        self._active_jobs[job.type_id] = self._active_jobs.get(job.type_id, 0) - 1
        if self._active_jobs[job.type_id] <= 0:
            self._active_jobs.pop(job.type_id)
