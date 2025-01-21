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

from typing import Dict, Any, Optional

from downloader.constants import K_DOWNLOADER_TIMEOUT
from downloader.job_system import WorkerResult
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.jobs.worker_context import DownloaderWorkerBase
from downloader.jobs.errors import FileDownloadError
import socket
from urllib.error import URLError
from http.client import HTTPException


class FetchFileWorker(DownloaderWorkerBase):
    def job_type_id(self) -> int: return FetchFileJob.type_id
    def reporter(self): return self._ctx.progress_reporter

    def operate_on(self, job: FetchFileJob) -> WorkerResult:
        error = self._fetch_file(job)
        if error is not None:
            return None, error

        return ValidateFileJob(fetch_job=job).set_priority(1), None

    def _fetch_file(self, job: FetchFileJob) -> Optional[FileDownloadError]:
        file_path, description = job.path, job.description
        target_path = self._ctx.file_system.download_target_path(self._ctx.target_path_repository.create_target(file_path, description))
        try:
            with self._ctx.http_gateway.open(description['url']) as (final_url, in_stream):
                description['url'] = final_url
                if in_stream.status != 200:
                    return FileDownloadError(f'Bad http status! {file_path}: {in_stream.status}')

                self._ctx.file_system.write_incoming_stream(in_stream, target_path, timeout=self._ctx.config[K_DOWNLOADER_TIMEOUT])

        except socket.gaierror as e:
            return FileDownloadError(f'Socket Address Error! {description["url"]}: {str(e)}')
        except URLError as e:
            return FileDownloadError(f'URL Error! {description["url"]}: {e.reason}')
        except HTTPException as e:
            return FileDownloadError(f'HTTP Error {type(e).__name__}! {description["url"]}: {str(e)}')
        except ConnectionResetError as e:
            return FileDownloadError(f'Connection reset error! {description["url"]}: {str(e)}')
        except OSError as e:
            return FileDownloadError(f'OS Error! {description["url"]}: {e.errno} {str(e)}')
        except BaseException as e:
            return FileDownloadError(f'Exception during download! {description["url"]}: {str(e)}')
