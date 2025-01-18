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

from downloader.constants import K_DOWNLOADER_TIMEOUT
from downloader.job_system import WorkerResult
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.worker_context import DownloaderWorker
from downloader.jobs.errors import FileDownloadError
import socket
from urllib.error import URLError
from http.client import HTTPException
from typing import Optional


class FetchFileWorker2(DownloaderWorker):
    def job_type_id(self) -> int: return FetchFileJob2.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: FetchFileJob2) -> WorkerResult:
        error = self._fetch_file(url=job.source, download_path=job.temp_path, info=job.info)
        if error is not None:
            return None, error

        return job.after_job, None

    def _fetch_file(self, url: str, download_path: str, info: str) -> Optional[FileDownloadError]:
        try:
            with self._ctx.http_gateway.open(url) as (final_url, in_stream):
                if in_stream.status != 200:
                    return FileDownloadError(f'Bad http status! {info}: {in_stream.status}')

                self._ctx.file_system.write_incoming_stream(in_stream, download_path, timeout=self._ctx.config[K_DOWNLOADER_TIMEOUT])

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

        if not self._ctx.file_system.is_file(download_path, use_cache=False):
            return FileDownloadError(f'Missing {info}')
