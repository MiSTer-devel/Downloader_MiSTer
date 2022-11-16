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
import ssl
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Tuple, Any, Optional, Generator
from urllib.parse import urlparse, ParseResult
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse, HTTPException

from downloader.logger import Logger


@dataclass
class _Connection:
    http: HTTPConnection
    last_use_time: float = 0.0
    timeout: float = 120.0

    def is_expired(self, now_time: float) -> bool:
        expire_time = self.last_use_time + self.timeout
        return now_time > expire_time


class HttpGateway:
    def __init__(self, ssl_ctx: ssl.SSLContext, timeout: int, logger: Logger = None):
        self._ssl_ctx = ssl_ctx
        self._timeout = timeout
        self._logger = logger
        self._connections = {}
        self._clean_connections_timer = time.time()

    def __enter__(self): return self
    def __exit__(self, *args, **kwargs): self.cleanup()

    def cleanup(self) -> None:
        if self._logger is not None: self._logger.debug(f'Cleaning up {len(self._connections)} connections.')
        for connection_id in self._connections:
            if self._connections[connection_id]:
                self._connections[connection_id].http.close()
        self._connections = {}

    @contextmanager
    def open(self, url: str, method: str = None, body: Any = None, headers: Any = None) -> Generator[Tuple[str, HTTPResponse], None, None]:
        if self._logger is not None: self._logger.debug('^^^^')
        self._clean_timeout_connections(time.time())
        result = self._open_impl(
            url,
            'GET' if method is None else method.upper(),
            body,
            headers or _default_headers,
            0
        )
        if self._logger is not None: self._logger.debug(f'HTTP {result[1].status}: {result[0]}\nvvvv\n')
        try:
            yield result
        finally:
            result[1].close()

    def _open_impl(self, url: str, method: str, body: Any, headers: Any, retry: int) -> Tuple[str, HTTPResponse]:
        retry, response = self._request(url, method, body, headers, retry)

        if self._logger is not None: self._logger.debug(f'Version: {response.version}\n{response.headers}')
        if 300 <= response.status < 400 and retry < 10:
            location = response.headers.get('location', None)
            if location is not None:
                if self._logger is not None: self._logger.debug(f'HTTP 3XX! Resource moved ({retry}): {url}')
                response.close()
                return self._open_impl(location, method, body, headers, retry + 1)

        return url, response

    def _request(self, url: str, method: str, body: Any, headers: Any, retry: int) -> Tuple[int, HTTPResponse]:
        parsed_url = urlparse(url)

        connection_id = parsed_url.scheme + parsed_url.netloc
        if connection_id not in self._connections:
            self._connections[connection_id] = _Connection(http=self._create_connection(parsed_url))

        connection = self._connections[connection_id]
        try:
            connection.http.request(method, self._request_url(parsed_url), headers=headers, body=body)
        except BrokenPipeError:
            pass
        try:
            response = connection.http.getresponse()
        except (HTTPException, OSError) as e:
            self._remove_connection(parsed_url)
            if retry < 10:
                if self._logger is not None: self._logger.debug(f'HTTP Exception! {type(e).__name__} ({retry}): {url} {str(e)}')
                return self._request(url, method, body, headers, retry + 1)
            else:
                raise e

        self._handle_keep_alive(connection, parsed_url, response)

        return retry, response

    def _handle_keep_alive(self, connection: _Connection, parsed_url: ParseResult, response: HTTPResponse) -> None:
        connection_header = response.headers.get('Connection', '').lower()
        if self._is_keep_alive_connection(response.version, connection_header):
            connection.last_use_time = time.time()
            keep_alive_timeout = self._get_keep_alive_timeout(connection_header, response.headers.get('Keep-Alive', ''))
            if keep_alive_timeout is not None:
                connection.timeout = keep_alive_timeout
        else:
            self._remove_connection(parsed_url)

    def _is_keep_alive_connection(self, version: int, connection_header: str) -> bool:
        is_keep_alive = (version == 10 and connection_header == 'keep-alive') or (version >= 11 and connection_header != 'close')
        if not is_keep_alive and self._logger is not None: self._logger.debug(f'Version: {version}, Connection: {connection_header}')
        return is_keep_alive

    def _get_keep_alive_timeout(self, connection_header: str, keep_alive_header: str) -> Optional[float]:
        if connection_header == '' or keep_alive_header == '':
            return None

        for p in keep_alive_header.split(','):
            kv = p.split('=')
            if len(kv) == 2 and kv[0].strip().lower() == 'timeout':
                try:
                    return float(kv[1].strip())
                except Exception as e:
                    if self._logger is not None: self._logger.debug(f"Could not parse keep-alive timeout on: {p}", e)
                    return None

        return None

    def _remove_connection(self, parsed_url: ParseResult):
        if self._logger is not None: self._logger.debug(f'Closing "{parsed_url.netloc}".')
        connection_id = parsed_url.scheme + parsed_url.netloc
        self._connections[connection_id].http.close()
        self._connections.pop(connection_id)

    @staticmethod
    def _request_url(parsed_url: ParseResult) -> str:
        url_path = parsed_url.path
        while len(url_path) > 0 and url_path[0] == '/':
            url_path = url_path.lstrip('/')
        return f'/{url_path}?{parsed_url.query}'.rstrip('?')

    def _create_connection(self, parsed_url: ParseResult) -> HTTPConnection:
        if parsed_url.scheme == 'http':
            return HTTPConnection(parsed_url.netloc, timeout=self._timeout)
        elif parsed_url.scheme == 'https':
            return HTTPSConnection(parsed_url.netloc, timeout=self._timeout, context=self._ssl_ctx)
        else:
            raise ValueError(f'Unsupported scheme "{parsed_url.scheme}" for url: {parsed_url.geturl()}')

    def _clean_timeout_connections(self, now: float):
        if now - self._clean_connections_timer < 30.0:
            return
        self._clean_connections_timer = now

        if self._logger is not None: self._logger.debug('Checking keep-alive timeouts...')
        connections_to_remove = []
        for connection_id in self._connections:
            connection = self._connections[connection_id]
            if connection.is_expired(now):
                connections_to_remove.append(connection_id)
                connection.http.close()

        for connection_id in connections_to_remove:
            self._connections.pop(connection_id)
            if self._logger is not None: self._logger.debug(f'Cleaning up connection "{connection_id}".')


_default_headers = {'Connection': 'Keep-Alive', 'Keep-Alive': 'timeout=120'}
