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
import datetime
import re
import tempfile
import sys
import time
import traceback
from typing import List, Any, Optional, Protocol

from downloader.config import Config


class Logger(Protocol):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True) -> None: """print always"""
    def debug(self, *args, sep='', end='\n', flush=True) -> None: """print only to debug target"""
    def bench(self, label: str) -> None: """print only to debug target"""


class PrintLogManager(Protocol):
    def configure(self, config: Config) -> None: pass

class PrintLogger(Logger, PrintLogManager):
    def __init__(self, start_time: Optional[int] = None):
        self._verbose_mode = True
        self._start_time = start_time

    def configure(self, config: Config):
        if config['verbose']:
            self._start_time = config['start_time']
        else:
            self._verbose_mode = False

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        _do_print(*args, sep=sep, end=end, file=file, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        if self._verbose_mode:
            exceptions = []
            for a in args:
                if isinstance(a, Exception):
                    exceptions.append(a)
            if len(exceptions) > 0:
                args = list(set(args) - set(exceptions))
                for e in exceptions:
                    _do_print("".join(traceback.format_exception(type(e), e, e.__traceback__)), sep=sep, end=end, file=sys.stdout, flush=flush)
            _do_print(*args, sep=sep, end=end, file=sys.stdout, flush=flush)

    def bench(self, label: str):
        if self._start_time is not None:
            _do_print('%s| %s' % (str(datetime.timedelta(seconds=time.time() - self._start_time))[0:-4], label), sep='', end='\n', file=sys.stdout, flush=True)

def _do_print(*args, sep, end, file, flush):
    try:
        print(*args, sep=sep, end=end, file=file, flush=flush)
    except UnicodeEncodeError:
        pack = []
        for a in args:
            pack.append(a.encode('utf8', 'surrogateescape'))
        print(*pack, sep=sep, end=end, file=file, flush=flush)
    except BaseException as error:
        print('An unknown exception occurred during logging: %s' % str(error))


class FilelogSaver(Protocol):
    def save_log_from_tmp(self, tmp_logfile: str) -> None: pass

class FilelogManager(Protocol):
    def finalize(self) -> None: pass
    def set_local_repository(self, local_repository: FilelogSaver) -> None: pass

class FileLoggerDecorator(Logger, FilelogManager):
    def __init__(self, decorated_logger: Logger):
        self._decorated_logger = decorated_logger
        self._logfile = tempfile.NamedTemporaryFile('w', delete=False)
        self._local_repository: Optional[FilelogSaver] = None

    def finalize(self):
        if self._logfile is None:
            return

        if self._local_repository is None:
            self.print('Log saved in temp file: ' + self._logfile.name)

        self._logfile.close()
        if self._local_repository is not None:
            self._local_repository.save_log_from_tmp(self._logfile.name)
        self._logfile = None

    def set_local_repository(self, local_repository: FilelogSaver):
        self._local_repository = local_repository

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        self._decorated_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
        self._do_print_in_file(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)
        self._do_print_in_file(*args, sep=sep, end=end, flush=flush)

    def bench(self, label: str):
        self._decorated_logger.bench(label)

    def _do_print_in_file(self, *args, sep, end, flush):
        if self._logfile is not None:
            print(*args, sep=sep, end=end, file=self._logfile, flush=flush)


class DebugOnlyLoggerDecorator(Logger):
    def __init__(self, decorated_logger: Logger):
        self._decorated_logger = decorated_logger

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """Calls debug instead of print"""
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def bench(self, label: str):
        self._decorated_logger.bench(label)


# @TODO: Consider moving this one to test code
class NoLogger(Logger, FilelogManager, PrintLogManager):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def bench(self, label: str): pass
    def finalize(self) -> None: pass
    def set_local_repository(self, local_repository: FilelogSaver) -> None: pass
    def configure(self, config: Config) -> None: pass


# @TODO: Consider moving this one to test code
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
                args[i] = f"{header}| {args[i].replace('\n', f"\n{header}| ")}"

        return args



def describe_time(t: float) -> str: return time.strftime(f'%Y-%m-%d %H:%M:%S.{t % 1 * 1000:03.0f}', time.localtime(t))
