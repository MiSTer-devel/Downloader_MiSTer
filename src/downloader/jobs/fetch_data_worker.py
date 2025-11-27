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

import io
import socket
from http.client import HTTPException
from urllib.error import URLError

from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import WorkerResult, ProgressReporter
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.worker_context import DownloaderWorker, JobErrorCtx
from downloader.jobs.errors import FileDownloadError, FileValidationError
from typing import Optional, Any


class FetchDataWorker(DownloaderWorker):
    def __init__(self, http_gateway: HttpGateway, file_system: FileSystem, progress_reporter: ProgressReporter, error_ctx: JobErrorCtx, timeout: int) -> None:
        self._http_gateway = http_gateway
        self._file_system = file_system
        self._progress_reporter = progress_reporter
        self._error_ctx = error_ctx
        self._timeout = timeout

    def job_type_id(self) -> int: return FetchDataJob.type_id
    def reporter(self): return self._progress_reporter

    def operate_on(self, job: FetchDataJob) -> WorkerResult:  # type: ignore[override]
        job.data, error = self._fetch_data(job.source, job.description.get('hash', None), job.description.get('size', None), job.calcs)
        if error is not None:
            self._error_ctx.swallow_error(error)
            return [], error

        return [] if job.after_job is None else [job.after_job], None

    def _fetch_data(self, url: str, valid_hash: Optional[str], valid_size: Optional[int], calcs: Optional[dict[str, Any]], /) -> tuple[Optional[io.BytesIO], Optional[Exception]]:
        try:
            with self._http_gateway.open(url) as (final_url, in_stream):
                if in_stream.status != 200:
                    return None, FileDownloadError(f'Bad http status! {final_url}: {in_stream.status}')

                return_calc_hash = valid_hash is not None or calcs is not None
                buf, calc_hash = self._file_system.write_stream_to_data(in_stream, return_calc_hash, self._timeout)
                calc_size = buf.getbuffer().nbytes

                if valid_hash is not None and calc_hash != valid_hash:
                    raise FileValidationError(f'Bad hash on {final_url} ({valid_hash} != {calc_hash})')
                if valid_size is not None:
                    if calc_size != valid_size:
                        raise FileValidationError(f'Bad size on {final_url} ({valid_size} != {calc_size})')
                if calcs is not None:
                    calcs['hash'] = calc_hash
                    calcs['size'] = calc_size

                return buf, None

        except socket.gaierror as e: return None, FileDownloadError(f'Socket Address Error! {url}: {str(e)}', e)
        except socket.timeout as e: return None, FileDownloadError(f'Socket Connection Timed Out! {url}: {str(e)}', e)
        except URLError as e: return None, FileDownloadError(f'URL Error! {url}: {e.reason}', e)
        except HTTPException as e: return None, FileDownloadError(f'HTTP Error! {url}: {str(e)}', e)
        except ConnectionResetError as e: return None, FileDownloadError(f'Connection reset error! {url}: {str(e)}', e)
        except OSError as e: return None, FileDownloadError(f'OS Error! {url}: {e.errno} {str(e)}', e)
        except Exception as e: return None, e
