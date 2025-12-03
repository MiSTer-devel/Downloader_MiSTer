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

from downloader.constants import SafeFetchInfo
from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import WorkerResult, ProgressReporter
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.errors import FileDownloadError, FileValidationError
import socket
from urllib.error import URLError
from http.client import HTTPException
from typing import Optional, TypedDict

from downloader.jobs.worker_context import DownloaderWorker
from downloader.logger import Logger
from downloader.waiter import Waiter


class FetchFileWorker(DownloaderWorker):
    def __init__(self, logger: Logger, progress_reporter: ProgressReporter, http_gateway: HttpGateway, file_system: FileSystem, timeout: int) -> None:
        self._logger = logger
        self._progress_reporter = progress_reporter
        self._file_system = file_system
        self._fetcher = FileFetcher(http_gateway=http_gateway, file_system=file_system, timeout=timeout)

    def job_type_id(self) -> int: return FetchFileJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: FetchFileJob) -> WorkerResult:  # type: ignore[override]
        source = job.source
        temp_path = job.pkg.temp_path(job.already_exists)
        backup_path = job.pkg.backup_path()
        target_path = job.pkg.full_path
        desc = job.pkg.description

        if temp_path is None and backup_path is not None and self._file_system.is_file(target_path, use_cache=False):  # @TODO: See if use_cache is needed
            self._file_system.copy(target_path, backup_path)

        file_path = temp_path or target_path
        file_size, file_hash, error = self._fetcher.fetch_file(source, file_path)
        if error is not None:
            return [], error

        try:
            if file_hash != desc['hash']:
                err = self._file_system.unlink(file_path, verbose=False)
                if err is not None:
                    self._logger.debug('WARNING: FetchFileWorker could not remove file_path ', file_path, err)
                return [], FileValidationError(f"Bad hash on {job.pkg.rel_path} ({desc['hash']} != {file_hash})")

            if file_path != target_path:
                if backup_path is not None and self._file_system.is_file(target_path, use_cache=False):  # @TODO: See if use_cache is needed
                    self._file_system.move(target_path, backup_path)
                self._file_system.move(file_path, target_path)

        except Exception as e:
            return [], FileDownloadError(f'Exception during validation! {job.pkg.rel_path}: {str(e)}')

        return [] if job.after_job is None else [job.after_job], None


class FileFetcher:
    def __init__(self, http_gateway: HttpGateway, file_system: FileSystem, timeout: int) -> None:
        self._http_gateway = http_gateway
        self._file_system = file_system
        self._timeout = timeout

    def fetch_file(self, url: str, download_path: str) -> tuple[int, str, Optional[FileDownloadError]]:
        try:
            with self._http_gateway.open(url) as (final_url, in_stream):
                if in_stream.status != 200:
                    return 0, '', FileDownloadError(f'Bad http status! {final_url}: {in_stream.status}')

                file_size, file_hash = self._file_system.write_incoming_stream(in_stream, download_path, self._timeout)

        except socket.gaierror as e: return 0, '', FileDownloadError(f'Socket Address Error! {url}: {str(e)}', e)
        except socket.timeout as e: return 0, '', FileDownloadError(f'Socket Connection Timed Out! {url}: {str(e)}', e)
        except URLError as e: return 0, '', FileDownloadError(f'URL Error! {url}: {e.reason}', e)
        except HTTPException as e: return 0, '', FileDownloadError(f'HTTP Error! {url}: {str(e)}', e)
        except ConnectionResetError as e: return 0, '', FileDownloadError(f'Connection reset error! {url}: {str(e)}', e)
        except OSError as e: return 0, '', FileDownloadError(f'OS Error! {url}: {e.errno} {str(e)}', e)
        except BaseException as e: return 0, '', FileDownloadError(f'Exception during download! {url}: {str(e)}')

        if not self._file_system.is_file(download_path, use_cache=False):
            return 0, '', FileDownloadError(f'File from {url} could not be stored.')

        return file_size, file_hash, None


class SafeFetcherConfig(TypedDict):
    downloader_timeout: int
    downloader_retries: int

class SafeFileFetcher:
    def __init__(self, config: SafeFetcherConfig, file_system: FileSystem, logger: Logger, http_gateway: HttpGateway, waiter: Waiter) -> None:
        self._retries = config['downloader_retries']
        self._logger = logger
        self._file_system = file_system
        self._waiter = waiter
        self._fetcher = FileFetcher(http_gateway, file_system, config['downloader_timeout'])

    def fetch_file(self, description: SafeFetchInfo, path: str) -> Optional[Exception]:
        i = self._retries
        while True:
            file_size, file_hash, error = self._fetcher.fetch_file(description['url'], path)
            if error is None:
                if file_hash != description['hash']:
                    error = FileValidationError(f'Hash mismatch! {description["url"]}: calculated hash {file_hash} != {description["hash"]}')

            if error is None:
                if file_size != description['size']:
                    error = FileValidationError(f'Size mismatch! {description["url"]}: calculated size {file_size} != {description["size"]}')

            i -= 1
            if error is None or i <= 0:
                break
            self._logger.print(f'Retrying {description["url"]}...')
            self._waiter.sleep(10)

        return error
