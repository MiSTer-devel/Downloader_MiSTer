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

import sys
from typing import Any, List
from downloader.config import Config
from downloader.logger import FilelogManager, FilelogSaver, Logger, PrintLogManager


class SpyLoggerDecorator(Logger):
    def __init__(self, decorated_logger):
        self._decorated_logger = decorated_logger
        self.printCalls = []
        self.debugCalls = []

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        self._decorated_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
        self.printCalls.append(args)

    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)
        self.debugCalls.append(args)

    def bench(self, *args):
        self._decorated_logger.bench(*args)


class NoLogger(Logger, FilelogManager, PrintLogManager):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def bench(self, *args): pass
    def finalize(self) -> None: pass
    def set_local_repository(self, local_repository: FilelogSaver) -> None: pass
    def configure(self, config: Config) -> None: pass


def describe_time(t: float) -> str: return time.strftime(f'%Y-%m-%d %H:%M:%S.{t % 1 * 1000:03.0f}', time.localtime(t))


class DescribeNowDecorator(Logger):
    def __init__(self, decorated_logger: Logger):
        self._re = re.compile(r'^ */[^:]+:\d+.*$')  # Matches paths such as /asd/bef/df:34
        self._decorated_logger = decorated_logger

    def bench(self, label: str): self._decorated_logger.bench(label)

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        self._decorated_logger.print(*self._handle_args([*args]), sep=sep, end=end, flush=True)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*self._handle_args([*args]), sep=sep, end=end, flush=True)

    def _handle_args(self, args: List[Any]) -> List[Any]:
        header = describe_time(time.time())
        for i in range(len(args)):
            if isinstance(args[i], str) and not self._re.fullmatch(args[i]):
                endln, replacement = '\n', f"\n{header}| "
                args[i] = f"{header}| {args[i].replace(endln, replacement)}"

        return args
