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

import ssl
import sys
import threading
import time
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
from typing import Tuple, Any, Optional, Generator, List, Dict, Union, Protocol, TypeVar
from urllib.parse import urlparse, ParseResult, urlunparse
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse, HTTPException, HTTPMessage


T = TypeVar('T')
class HttpGatewayException(Exception): pass

class Logger(Protocol):
    def print(self, msg: str) -> None: ...
    def debug(self, msg: str, e: Exception = None) -> None: ...


class HttpGateway:
    def __init__(self, ssl_ctx: ssl.SSLContext, timeout: int, logger: Logger = None):
        now = time.time()
        self._ssl_ctx = ssl_ctx
        self._timeout = timeout
        self._logger = logger
        self._connections: Dict[_QueueId, _ConnectionQueue] = {}
        self._connections_lock = threading.Lock()
        self._clean_timeout_connections_timer = now
        self._clean_timeout_connections_lock = threading.Lock()
        self._queue_redirects: Dict[_QueueId, _Redirect[_QueueId]] = {}
        self._queue_redirects_lock = threading.Lock()
        self._url_redirects: Dict[str, _Redirect[str]] = {}
        self._url_redirects_lock = threading.Lock()
        self._redirects_swap: Dict[T, _Redirect[T]] = {}
        self._clean_timeout_redirects_timer = now
        self._clean_timeout_redirects_lock = threading.Lock()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self._logger is not None:
            self._logger.print(f"An exception of type {exc_type} occurred with value {exc_val}. Traceback: {exc_tb}")

        self.cleanup()
        return False

    @contextmanager
    def open(self, url: str, method: str = None, body: Any = None, headers: Any = None) -> Generator[Tuple[str, HTTPResponse], None, None]:
        now = time.time()
        self._clean_timeout_connections(now)
        self._clean_timeout_redirects(now)

        method = 'GET' if method is None else method.upper()
        if self._logger is not None: self._logger.debug(f'^^^^ {method} {url}\n{describe_time(now)}')
        url = self._process_url(url)
        parsed_url = urlparse(url)
        final_url, conn, _ = self._request(
            url,
            parsed_url,
            method,
            body,
            headers or _default_headers,
            0
        )
        if self._logger is not None: self._logger.debug(f'HTTP {conn.response.status}: {final_url}\n'
                                                        f'1st byte @ {describe_time(t := time.time())} ({t - now:.3f}s)\nvvvv\n')
        try:
            yield final_url, conn.response
        finally:
            conn.finish_response()
            if self._logger is not None: self._logger.debug(f'|||| Done {describe_time(t := time.time())}: {final_url} ({t - now:.3f}s)')

    def cleanup(self) -> None:
        total_cleared = 0
        with self._connections_lock:
            for queue in self._connections.values():
                total_cleared += queue.clear_all()
            self._connections.clear()
        if self._logger is not None: self._logger.debug(f'Cleaning up {total_cleared} connections.')
        with self._queue_redirects_lock: self._queue_redirects.clear()
        with self._url_redirects_lock: self._url_redirects.clear()

    def _request(self, url: str, parsed_url: ParseResult, method: str, body: Any, headers: Any, retry: int) -> Tuple[str, '_Connection', int]:
        if retry > 2: time.sleep(retry * retry * retry * 0.0001)
        queue_id: _QueueId = self._process_queue_id((parsed_url.scheme, parsed_url.netloc))
        conn = self._take_connection(queue_id)
        try:
            conn.do_request(method, str(urlunparse(parsed_url)), body, headers)
        except (HTTPException, OSError) as e:
            conn.kill()
            if retry < 10:
                if self._logger is not None: self._logger.debug(f'HTTP Exception! {type(e).__name__} ({retry}) {describe_time(time.time())} [{url}] {str(e)}\n'
                                                                f'Killed "{parsed_url.scheme}://{parsed_url.netloc}" connection {conn.id}.\n')
                return self._request(url, parsed_url, method, body, headers, retry + 1)
            else:
                raise e

        if self._logger is not None: self._logger.debug(conn.describe())

        if 300 <= conn.response.status < 400 and retry < 10:
            location, parsed_location = self._follow_move(conn, queue_id, url, parsed_url)
            return self._request(location, parsed_location, method, body, headers, retry + 1)

        return url, conn, retry

    def _follow_move(self, conn: '_Connection', queue_id: '_QueueId', url: str, parsed_url: ParseResult) -> Tuple[str, ParseResult]:
        location, redirect_timeout = conn.response_headers.redirect_params(conn.response.status)
        if location is None:
            raise HttpGatewayException('Invalid header response during Resource moved response at ' + url)

        if self._logger is not None: self._logger.debug(f'HTTP {conn.response.status}! Resource moved: {url} -> {location} [{describe_time(time.time())}]\n\n')
        conn.finish_response()

        if location[0] == '/':
            location = f'{parsed_url.scheme}://{parsed_url.netloc}{location}'

        location = self._process_url(location)
        parsed_location = urlparse(location)

        if redirect_timeout is not None:
            if (parsed_location.path == parsed_url.path and
                parsed_location.query == parsed_url.query and
                parsed_location.params == parsed_url.params and
                parsed_location.fragment == parsed_url.fragment
            ):
                target_queue_id: _QueueId = (parsed_location.scheme, parsed_location.netloc)
                if target_queue_id != queue_id:
                    redirect = _Redirect(target_queue_id, redirect_timeout)
                    with self._queue_redirects_lock:
                        self._queue_redirects[queue_id] = redirect

            elif url != location:
                redirect = _Redirect(location, redirect_timeout)
                with self._url_redirects_lock:
                    self._url_redirects[url] = redirect

        return location, parsed_location

    def _process_url(self, url: str) -> str: return _redirect(url, self._url_redirects, self._url_redirects_lock)
    def _process_queue_id(self, queue_id: '_QueueId') -> '_QueueId': return _redirect(queue_id, self._queue_redirects, self._queue_redirects_lock)

    def _take_connection(self, queue_id: '_QueueId') -> '_Connection':
        with self._connections_lock:
            if queue_id not in self._connections:
                self._connections[queue_id] = _ConnectionQueue(queue_id, self._timeout, self._ssl_ctx, self._logger)
            return self._connections[queue_id].pull()

    def _clean_timeout_connections(self, now: float) -> None:
        if now - self._clean_timeout_connections_timer < 30.0:
            return

        if not self._clean_timeout_connections_lock.acquire(blocking=False):
            return

        try:
            if now - self._clean_timeout_connections_timer < 30.0:
                return

            self._clean_timeout_connections_timer = now
            if self._logger is not None: self._logger.debug('Checking keep-alive timeouts...')

            connection_items: List[Tuple[Tuple[str, str], _ConnectionQueue]]
            with self._connections_lock:
                connection_items = list(self._connections.items())

            for queue_id, queue in connection_items:
                cleaned_up_connections = queue.clear_timed_outs(now)
                if cleaned_up_connections > 0 and self._logger is not None:
                    self._logger.debug(f'Cleaning up {cleaned_up_connections} connections on queue: "{queue_id}".')

        finally:
            self._clean_timeout_connections_lock.release()

    def _clean_timeout_redirects(self, now: float) -> None:
        if now - self._clean_timeout_redirects_timer < 30.0:
            return

        if not self._clean_timeout_redirects_lock.acquire(blocking=False):
            return

        try:
            if now - self._clean_timeout_redirects_timer < 30.0:
                return

            self._clean_timeout_redirects_timer = now
            if self._logger is not None: self._logger.debug('Checking redirect timeouts...')

            if self._fill_redirects_swap(now, self._queue_redirects_lock, self._queue_redirects):
                with self._queue_redirects_lock:
                    self._queue_redirects, self._redirects_swap = self._redirects_swap, self._queue_redirects

            if self._fill_redirects_swap(now, self._url_redirects_lock, self._url_redirects):
                with self._url_redirects_lock:
                    self._url_redirects, self._redirects_swap = self._redirects_swap, self._url_redirects

        finally:
            self._clean_timeout_redirects_lock.release()

    def _fill_redirects_swap(self, now: float, lock: threading.Lock, redirects: Dict[T, '_Redirect[T]']) -> bool:
        # We are minimizing lock time, by doing most of the operations in redirect_items and self._redirects_swap.
        # If we see that redirects needs to change, we return True to indicate that it needs to be swapped outside.

        self._redirects_swap.clear()
        redirect_items: List[Tuple[T, _Redirect[T]]]

        with lock:
            size = len(redirects)
            if size == 0: return False
            redirect_items = list(redirects.items())

        for key, redirect in redirect_items:
            if not redirect.is_expired(now):
                self._redirects_swap[key] = redirect

        return size != len(self._redirects_swap)

_default_headers = {'Connection': 'keep-alive', 'Keep-Alive': 'timeout=120'}


_QueueId = Tuple[str, str]

class _Redirect[T]:
    def __init__(self, target: T, timeout: float):
        self.target = target
        self.timeout = timeout

    def is_expired(self, now: float) -> bool:
        return now > self.timeout

def _redirect(input_arg: T, res_dict: Dict[T, _Redirect[T]], lock: threading.Lock) -> T:
    redirects = 0
    arg = input_arg
    with lock:
        while arg in res_dict and redirects < 10:
            arg = res_dict[arg].target
            redirects += 1

        if redirects > 1:  # When redirecting, only 1 redirect should be enough, so we prepare the dict for the next run.
            res_dict[input_arg].target = arg

    return arg


class _Connection:
    def __init__(self, conn_id: int, http: HTTPConnection, connection_queue: '_ConnectionQueue', logger: Optional[Logger]):
        self.id = conn_id
        self._http = http
        self._connection_queue = connection_queue
        self._logger = logger
        self._timeout = http.timeout if http.timeout is not None else 120.0
        self._last_use_time: float = 0.0
        self._uses: int = 0
        self._max_uses: int = sys.maxsize
        self._response: Optional[Union[HTTPResponse, '_FinishedResponse']] = None
        self._response_headers = _ResponseHeaders(logger)

    def is_expired(self, now_time: float) -> bool:
        expire_time = self._last_use_time + self._timeout
        return now_time > expire_time

    def do_request(self, method: str, url: str, body: Any, headers: Any) -> None:
        self._http.request(method, url, headers=headers, body=body)
        self._uses += 1
        self._response = self._http.getresponse()
        self._response_headers.set_headers(self._response.headers, self._response.version)
        self._handle_keep_alive()

    def kill(self) -> None:
        self._close_response()
        self._http.close()
        self._last_use_time = 0
        self._timeout = 0

    @property
    def response(self) -> HTTPResponse:
        if self._response is None: raise HttpGatewayException('No response available.')
        elif isinstance(self._response, _FinishedResponse): raise HttpGatewayException('Response is already finished.')
        return self._response

    @property
    def response_headers(self) -> '_ResponseHeaders':
        return self._response_headers

    def finish_response(self):
        if self._close_response() and self._uses < self._max_uses:
            self._connection_queue.push(self)

    def _close_response(self) -> bool:
        if isinstance(self._response, _FinishedResponse):
            return False
        if self._response is not None:
            self._response.close()
        self._response = _FinishedResponse()
        return True

    def describe(self) -> str:
        return (
            f'[conn obj id={self._connection_queue.id[0]}://{self._connection_queue.id[1]}/{self.id}, '
                f'uses={self._uses}, max_uses={self._max_uses}, timeout={self._timeout}, last_use_time={self._last_use_time}]\n'
            f'Response HTTP Ver.{self.response.version} | Headers\n------------------------------\n'
            f'{self.response.headers}'
        )

    def _handle_keep_alive(self):
        if not self._response_headers.is_keep_alive_connection():
            self._logger.debug(f'Keep-Alive off')
            self._max_uses = 0
            return

        self._last_use_time = time.time()
        keep_alive_timeout, keep_alive_max = self.response_headers.keep_alive_params()
        if keep_alive_timeout is not None: self._timeout = keep_alive_timeout
        if keep_alive_max is not None: self._max_uses = keep_alive_max


class _ConnectionQueue:
    def __init__(self, queue_id: _QueueId, timeout: int, ctx: ssl.SSLContext, logger: Optional[Logger]):
        self.id = queue_id
        self._timeout = timeout
        self._ctx = ctx
        self._logger = logger
        self._queue: List[_Connection] = []
        self._queue_swap: List[_Connection] = []
        self._lock = threading.Lock()
        self._last_conn_id = -1

    def pull(self) -> _Connection:
        with self._lock:
            if len(self._queue) == 0:
                self._last_conn_id += 1
                return _Connection(
                    conn_id=self._last_conn_id,
                    http=self._create_http_connection(),
                    connection_queue=self,
                    logger=self._logger
                )
            return self._queue.pop()

    def push(self, connection: _Connection) -> None:
        with self._lock:
            self._queue.append(connection)

    def clear_all(self) -> int:
        with self._lock:
            size = len(self._queue)
            for connection in self._queue:
                connection.kill()

            self._queue, self._queue_swap = self._queue_swap, self._queue
            self._queue.clear()
            return size

    def clear_timed_outs(self, now: float) -> int:
        with self._lock:
            expired_count = 0
            self._queue, self._queue_swap = self._queue_swap, self._queue
            self._queue.clear()

            for connection in self._queue_swap:
                if connection.is_expired(now):
                    connection.kill()
                    expired_count += 1
                else:
                    self._queue.append(connection)

            return expired_count

    def _create_http_connection(self) -> HTTPConnection:
        scheme, netloc = self.id[0], self.id[1]
        if scheme == 'http':
            return HTTPConnection(netloc, timeout=self._timeout)
        elif scheme == 'https':
            return HTTPSConnection(netloc, timeout=self._timeout, context=self._ctx)
        else:
            if self._logger: self._logger.debug(f"Scheme {scheme} not supported. Using default HTTPConnection.")
            return HTTPConnection(netloc, timeout=self._timeout)


class _FinishedResponse: pass


class _ResponseHeaders:
    def __init__(self, logger: Optional[Logger]):
        self._logger = logger
        self._headers: Optional[HTTPMessage] = None
        self._version = 11
        self._params_parser = _ParamsParser(logger)

    def set_headers(self, headers: HTTPMessage, version: int) -> None:
        self._headers = headers
        self._version = version

    @property
    def headers(self) -> HTTPMessage:
        if self._headers is None: raise HttpGatewayException('Set headers before accessing them.')
        return self._headers

    def redirect_params(self, status: int) -> Tuple[Optional[str], Optional[float]]:
        new_url = self.headers.get('location', None)
        if new_url is None:
            return None, None

        cache_control = self.headers.get('cache-control', None)
        if cache_control is not None:
            self._params_parser.parse(cache_control)
            if self._params_parser.bool('no-cache') or self._params_parser.bool('no-store'):
                return new_url, None

            max_age = self._params_parser.int('max-age')
            if max_age is not None:
                if max_age <= 0:
                    return new_url, None

                age = self.headers.get('age', '0')
                try:
                    age = int(age)
                except Exception as e:
                    if self._logger is not None: self._logger.debug(f"Could not parse Age from {age}", e)
                    age = 0

                return new_url, time.time() + max_age - age

            pass

        expires = self.headers.get('expires', None)
        if expires is not None:
            try:
                return new_url, parsedate_to_datetime(expires).timestamp()
            except Exception as e:
                if self._logger is not None: self._logger.debug(f"Could not parse Expires from {expires}", e)

        if status == 300 or status == 301:
            return new_url, time.time() + 60 * 60 * 24  # Permanent redirects, caching 1 day by default

        return new_url, None  # Temporary redirects, no cache by default

    def is_keep_alive_connection(self):
        connection = self.headers.get('connection', '').lower()
        is_keep_alive = (self._version == 10 and connection == 'keep-alive') or (self._version >= 11 and connection != 'close')
        return is_keep_alive

    def keep_alive_params(self) -> Tuple[Optional[float], Optional[float]]:
        keep_alive_header = self.headers.get('keep-alive', None)
        if keep_alive_header is None: return None, None
        self._params_parser.parse(keep_alive_header)
        return self._params_parser.int('timeout'), self._params_parser.int('max')


class _ParamsParser:
    def __init__(self, logger: Optional[Logger]):
        self._logger = logger
        self._data = dict()

    def parse(self, source: Optional[str]) -> '_ParamsParser':
        if source is None: return self
        self._data.clear()
        for p in source.lower().split(','):
            kv = p.split('=')
            if len(kv) == 1: self._data[kv[0]] = True
            elif len(kv) == 2: self._data[kv[0]] =  kv[1]
            elif self._logger is not None: self._logger.debug(f"ERROR! Could not parse param '{p}' from: {source}")
        return self

    def bool(self, key: str) -> bool:
        if key not in self._data: return False
        if self._data[key] is True: return True
        if self._logger is not None: self._logger.debug(f"ERROR! Could not parse bool '{key}' from: {self._data[key]}")
        return False

    def int(self, key: str) -> Optional[int]:
        if key not in self._data: return None
        try:
            return int(self._data[key])
        except Exception as e:
            if self._logger is not None: self._logger.debug(f"ERROR! Could not parse int '{key}' from: {self._data[key]}", e)
            return None

    def str(self, key: str) -> Optional[str]:
        if key not in self._data: return None
        return self._data[key]

def describe_time(t: float) -> str: return time.strftime(f'%Y-%m-%d %H:%M:%S.{t % 1 * 1000:03.0f}', time.localtime(t))