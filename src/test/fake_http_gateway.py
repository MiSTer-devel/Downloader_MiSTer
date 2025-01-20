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

from typing import Dict, Any, Tuple, Generator, Optional
from contextlib import contextmanager

from downloader.job_system import Job
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from test.objects import binary_content


class FakeHttpGateway:
    def __init__(self, config, network_state):
        self._config = config
        self._network_state = network_state
        self._job: Optional[Job] = None

    def set_job(self, job: Optional[Job]) -> None:
        self._job = job

    @contextmanager
    def open(self, url: str, _method: str = None, _body: Any = None, _headers: Any = None) -> Generator[Tuple[str, 'FakeHTTPResponse'], None, None]:
        description = None
        target_file_path = None
        info_path = None
        if isinstance(self._job, FetchFileJob):
            description = {**self._job.description}
            target_file_path = self._job.path
        elif isinstance(self._job, FetchFileJob2):
            if isinstance(self._job.after_job, ValidateFileJob2):
                description = {**self._job.after_job.description}

            if info_path is None:
                info_path = self._job.info
            target_file_path = self._job.temp_path

        match_path = info_path if info_path is not None else target_file_path if target_file_path is not None else url

        status = 200
        self._network_state.remote_failures[match_path] = self._network_state.remote_failures.get(match_path, 0)
        self._network_state.remote_failures[match_path] -= 1
        if self._network_state.remote_failures[match_path] > 0:
            status = 404

        description = {**self._network_state.remote_files[match_path]} if match_path in self._network_state.remote_files else description
        if description is None:
            description = {'hash': match_path, 'size': 1}
        if 'url' in description:
            del description['url']
        if 'delete' in description:
            del description['delete']

        storing_problems = match_path in self._network_state.storing_problems and self._network_state.storing_problems[match_path] > 0
        if storing_problems:
            self._network_state.storing_problems[match_path] -= 1

        yield url, FakeHTTPResponse(
            url=url,
            status=status,
            storing_problems=storing_problems,
            description=description,
            file_path=target_file_path
        )

    def cleanup(self) -> None:
        pass


class FakeHTTPResponse:
    def __init__(self, url: str, status: int, storing_problems: bool, description: Optional[Dict[str, Any]], file_path: Optional[str]):
        self.url = url
        self.status = status
        self.storing_problems = storing_problems
        self.description = description
        self.file_path = file_path
        self._position = 0

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            result = binary_content[self._position:]
            self._position = len(binary_content)
        else:
            result = binary_content[self._position:self._position + size]
            self._position += size
        return result
