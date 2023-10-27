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

import socket
import abc
import dataclasses
import time
from http.client import HTTPException
from typing import Dict, Optional, Tuple, List, Any
from urllib.error import URLError

from downloader.db_entity import DbEntity
from downloader.file_filter import BadFileFilterPartException
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.errors import FileDownloadException
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.validate_file_job2 import ValidateFileJob2
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
    path: str
    target_path: str
    desc: Dict[str, Any]
    db_id: str


class InstallationReport(abc.ABC):
    def processed_file(self, path: str) -> ProcessedFile: """File that a database is currently processing."""
    def downloaded_files(self) -> List[str]: """Files that has just been downloaded and validated."""
    def already_present_files(self) -> List[str]: """File previously in the system, that were not in the store, and now have been validated."""
    def fetch_started_files(self) -> List[str]: """Files that have been queued for download."""
    def failed_files(self) -> List[str]: """Files that couldn't be downloaded properly or didn't pass validation."""
    def removed_files(self) -> List[str]: """Files that have just been removed."""
    def installed_files(self) -> List[str]: """Files that have just been installed and need to be updated in the store."""
    def uninstalled_files(self) -> List[str]: """Files that have just been uninstalled for various reasons and need to be removed from the store."""
    def wrong_db_options(self) -> List[WrongDatabaseOptions]: """Databases that have been unprocessed because of their database."""

    def skipped_updated_files(self) -> List[str]: """File with an available update that didn't get updated because it has override false in its file description."""


class InstallationReportImpl(InstallationReport):
    def __init__(self):
        self._downloaded_files = []
        self._already_present_files = []
        self._fetch_started_files = []
        self._failed_files = []
        self._failed_db_options: List[WrongDatabaseOptions] = []
        self._removed_files = []
        self._skipped_updated_files = []
        self._processed_files: Dict[str, ProcessedFile] = {}

    def add_downloaded_file(self, path: str): self._downloaded_files.append(path)
    def add_already_present_file(self, path: str): self._already_present_files.append(path)
    def add_file_fetch_started(self, path: str): self._fetch_started_files.append(path)
    def add_failed_file(self, path: str): self._failed_files.append(path)
    def add_failed_db_options(self, exception: WrongDatabaseOptions): self._failed_db_options.append(exception)
    def add_removed_file(self, path: str): self._removed_files.append(path)
    def is_file_processed(self, path: str) -> bool: return path in self._processed_files
    def add_processed_file(self, target_path: str, path: str, desc: Dict[str, Any], db_id: str): self._processed_files[path] = ProcessedFile(path, target_path, desc, db_id)
    def add_skipped_updated_file(self, path: str): self._skipped_updated_files.append(path)
    def processed_file(self, path: str) -> ProcessedFile: return self._processed_files[path]
    def downloaded_files(self): return self._downloaded_files
    def already_present_files(self): return self._already_present_files
    def fetch_started_files(self): return self._fetch_started_files
    def failed_files(self): return self._failed_files
    def removed_files(self): return self._removed_files
    def installed_files(self): return self._downloaded_files + self._already_present_files
    def uninstalled_files(self): return self._removed_files + self._failed_files
    def wrong_db_options(self): return self._failed_db_options
    def skipped_updated_files(self): return self._skipped_updated_files


class FileDownloadProgressReporter(ProgressReporter):

    def __init__(self, logger: Logger, waiter: Waiter, report: InstallationReportImpl):
        self._logger = logger
        self._waiter = waiter
        self._report = report
        self._check_time: float = 0
        self._active_jobs: Dict[int] = {}
        self._deactivated: bool = False
        self._needs_newline: bool = False
        self._need_clear_header: bool = False
        self._symbols: List[str] = []

    def start_session(self):
        self.__init__(self._logger, self._waiter, InstallationReportImpl())

    def _deactivate(self):
        self._deactivated = True

    def is_active(self) -> bool:
        return len(self._active_jobs) > 0 and not self._deactivated

    def report(self) -> InstallationReport:
        return self._report

    def notify_job_started(self, job: Job):
        if isinstance(job, FetchFileJob):
            self._print_line(job.path)
            self._report.add_file_fetch_started(job.path)
        if isinstance(job, FetchFileJob2) and not job.silent:
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
        if isinstance(job, FetchFileJob) or isinstance(job, FetchFileJob2):
            self._symbols.append('.')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

        elif isinstance(job, ValidateFileJob):
            self._symbols.append('+')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

            self._report.add_downloaded_file(job.fetch_job.path)
        elif isinstance(job, ValidateFileJob2):
            self._symbols.append('+')
            if self._needs_newline or self._check_time < time.time():
                self._print_symbols()

            self._report.add_downloaded_file(job.fetch_job.info)

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
        if isinstance(job, ProcessDbJob) and isinstance(exception, BadFileFilterPartException):
            self._report.add_failed_db_options(
                WrongDatabaseOptions(f"Wrong custom download filter on database {job.db.db_id}. Part '{str(exception)}' is invalid.")
            )
        result = self._url_path_from_job(job)
        if result is not None:
            _, path = result
            self._report.add_failed_file(path)
        self.notify_job_retried(job, exception)

    def notify_job_retried(self, job: Job, exception: BaseException):
        self._logger.debug(self._message_from_exception(job, exception))
        self._logger.debug(exception)
        self._symbols.append('~')
        self._print_symbols()
        self._remove_in_progress(job)

    def _url_path_from_job(self, job: Job) -> Optional[Tuple[str, str]]:
        if isinstance(job, ValidateFileJob) or isinstance(job, ValidateFileJob2):
            job = job.fetch_job
        if isinstance(job, FetchFileJob):
            url, path = job.description.get('url', None) or '', job.path
        elif isinstance(job, FetchFileJob2):
            url, path = job.url, job.info
        else:
            return None
        return url, path

    def _message_from_exception(self, job: Job, exception: BaseException):
        result = self._url_path_from_job(job)
        if result is None:
            return str(exception)

        url, path = result

        try:
            raise exception
        except socket.gaierror as e:
            return f'Socket Address Error! {url}: {str(e)}'
        except URLError as e:
            return f'URL Error! {url}: {e.reason}'
        except HTTPException as e:
            return f'HTTP Error {type(e).__name__}! {url}: {str(e)}'
        except ConnectionResetError as e:
            return f'Connection reset error! {url}: {str(e)}'
        except OSError as e:
            return f'OS Error! {url}: {e.errno} {str(e)}'
        except FileDownloadException as e:
            return str(e)
        except BaseException as e:
            return f'Exception during download! {url}: {str(e)}'

    def _remove_in_progress(self, job: Job):
        self._active_jobs[job.type_id] = self._active_jobs.get(job.type_id, 0) - 1
        if self._active_jobs[job.type_id] <= 0:
            self._active_jobs.pop(job.type_id)
