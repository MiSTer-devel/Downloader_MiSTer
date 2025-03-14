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

from typing import Dict, Any, Tuple, Generator, Optional, TypedDict
from contextlib import contextmanager
import ssl

from downloader.http_gateway import HttpGateway
from test.objects import binary_content


class FileContextRequired(TypedDict):
    description: Dict[str, Any]
    path: str

class FileContext(FileContextRequired, total=False):
    info: str

class FakeHttpGateway(HttpGateway):
    def __init__(self, config, network_state):
        super().__init__(ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT), 200, None)
        self._config = config
        self._network_state = network_state
        self._file_ctx: Optional[FileContext] = None

    def set_file_ctx(self, file_ctx: Optional[Tuple[FileContext, str]]) -> None:
        self._file_ctx = file_ctx

    @contextmanager
    def open(self, url: str, _method: str = None, _body: Any = None, _headers: Any = None) -> Generator[Tuple[str, 'FakeHTTPResponse'], None, None]:
        description = None
        target_file_path = None
        info_path = None
        if self._file_ctx is not None:
            description, target_file_path, info_path = self._file_ctx['description'], self._file_ctx['path'], self._file_ctx.get('info', None)

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
        self.buf = FakeBuf(description)
        self._position = 0

    def read(self, size: int = -1) -> bytes:
        if size == -1:
            result = binary_content[self._position:]
            self._position = len(binary_content)
        else:
            result = binary_content[self._position:self._position + size]
            self._position += size
        return result

class FakeBuf:
    def __init__(self, description):
        self.description = description
        self.nbytes = description.get('size', 1)

    def getbuffer(self): return self
    def seek(self, n: int): pass
    def read(self): return b'0'
