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

from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import WorkerResult, ProgressReporter
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadError
import socket
from urllib.error import URLError
from http.client import HTTPException
from typing import Optional, TypedDict

from downloader.logger import Logger
from downloader.waiter import Waiter


class FetchFileWorker2(DownloaderWorker):
    def __init__(self, progress_reporter: ProgressReporter, http_gateway: HttpGateway, file_system: FileSystem, timeout: int):
        self._progress_reporter = progress_reporter
        self._fetcher = FileFetcher(http_gateway=http_gateway, file_system=file_system, timeout=timeout)

    def job_type_id(self) -> int: return FetchFileJob2.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: FetchFileJob2) -> WorkerResult:  # type: ignore[override]
        error = self._fetcher.fetch_file(url=job.source, download_path=job.temp_path)
        if error is not None:
            return [], error

        return [] if job.after_job is None else [job.after_job], None


class FileFetcher:
    def __init__(self, http_gateway: HttpGateway, file_system: FileSystem, timeout: int):
        self._http_gateway = http_gateway
        self._file_system = file_system
        self._timeout = timeout

    def fetch_file(self, url: str, download_path: str) -> Optional[FileDownloadError]:
        try:
            with self._http_gateway.open(url) as (final_url, in_stream):
                if in_stream.status != 200:
                    return FileDownloadError(f'Bad http status! {final_url}: {in_stream.status}')

                self._file_system.write_incoming_stream(in_stream, download_path, timeout=self._timeout)

        except socket.gaierror as e:
            return FileDownloadError(f'Socket Address Error! {url}: {str(e)}')
        except URLError as e:
            return FileDownloadError(f'URL Error! {url}: {e.reason}')
        except HTTPException as e:
            return FileDownloadError(f'HTTP Error {type(e).__name__}! {url}: {str(e)}')
        except ConnectionResetError as e:
            return FileDownloadError(f'Connection reset error! {url}: {str(e)}')
        except OSError as e:
            return FileDownloadError(f'OS Error! {url}: {e.errno} {str(e)}')
        except BaseException as e:
            return FileDownloadError(f'Exception during download! {url}: {str(e)}')

        if not self._file_system.is_file(download_path, use_cache=False):
            return FileDownloadError(f'File from {url} could not be stored.')

        return None


class SafeFetchInfo(TypedDict):
    url: str
    hash: str
    size: int

class SafeFetcherConfig(TypedDict):
    downloader_timeout: int
    downloader_retries: int

class SafeFileFetcher:
    def __init__(self, config: SafeFetcherConfig, file_system: FileSystem, logger: Logger, http_gateway: HttpGateway, waiter: Waiter):
        self._retries = config['downloader_retries']
        self._logger = logger
        self._file_system = file_system
        self._waiter = waiter
        self._fetcher = FileFetcher(http_gateway, file_system, config['downloader_timeout'])

    def fetch_file(self, description: SafeFetchInfo, path: str) -> Optional[FileDownloadError]:
        i = self._retries
        while True:
            error = self._fetcher.fetch_file(description['url'], path)
            if error is None:
                calculated_hash = self._file_system.hash(path)
                if calculated_hash != description['hash']:
                    error = FileDownloadError(f'Hash mismatch! {description['url']}: calculated hash {calculated_hash} != {description['hash']}')

            if error is None:
                calculated_size = self._file_system.size(path)
                if calculated_size != description['size']:
                    error = FileDownloadError(f'Size mismatch! {description['url']}: calculated size {calculated_size} != {description['size']}')

            i -= 1
            if error is None or i <= 0:
                break
            self._logger.print(f'Retrying {description['url']}...')
            self._waiter.sleep(10)

        return error
