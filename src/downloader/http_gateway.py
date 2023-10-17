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

from contextlib import contextmanager
from typing import Any, Generator, Tuple, Optional
import ssl
from . import urllib3


class HttpGateway:
    def __init__(self, ssl_ctx: ssl.SSLContext, timeout: int, logger: Optional = None):
        self._timeout = timeout
        self._logger = logger
        connection_pool_kw = {
            "timeout": self._timeout,
            "ssl_context": ssl_ctx,  # Directly use SSLContext object here
            "retries": urllib3.Retry(10, redirect=10)
        }
        self._http = urllib3.PoolManager(**connection_pool_kw)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self._logger:
            self._logger.print(f"An exception of type {exc_type} occurred with value {exc_val}. Traceback: {exc_tb}")

    @contextmanager
    def open(self, url: str, method: str = "GET", body: Any = None, headers: Optional = None) -> Generator[Tuple[str, Any], None, None]:
        response = self._http.request(
            method,
            url,
            body=body,
            headers=headers,
            preload_content=False,
        )

        final_url = response.geturl() or url

        if self._logger:
            self._logger.debug(f"HTTP {response.status}: {final_url}")

        try:
            yield final_url, response
        finally:
            response.release_conn()

    def cleanup(self):
        pass
