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
import datetime
import tempfile
import sys
import time
import traceback
from typing import Any, Optional, Protocol, TextIO, cast

from downloader.config import Config


class Logger(Protocol):
    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=True) -> None: """print always"""
    def debug(self, *args: Any, sep: str='', end: str='\n', flush: bool=True) -> None: """print only to debug target"""
    def bench(self, *args: Any) -> None: """print only to debug target"""


class PrintLogger(Logger):
    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=True) -> None:
        _do_print(*args, sep=sep, end=end, file=file, flush=flush)

    def debug(self, *args: Any, sep: str='', end: str='\n', flush: bool=True) -> None:
        _do_print("DEBUG| ", *args, sep=sep, end=end, file=sys.stdout, flush=flush)

    def bench(self, *args: Any) -> None:
        _do_print(*args, sep='', end='\n', file=sys.stdout, flush=True)

def _do_print(*args: Any, sep: str, end: str, file: TextIO, flush: bool) -> None:
    try:
        print(*args, sep=sep, end=end, file=file, flush=flush)
    except UnicodeEncodeError:
        pack = []
        for a in args:
            pack.append(a.encode('utf8', 'surrogateescape'))
        print(*pack, sep=sep, end=end, file=file, flush=flush)
    except BaseException as error:
        print('An unknown exception occurred during logging: %s' % str(error))


class OffLogger(Logger):
    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=False) -> None: pass
    def debug(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=False) -> None: pass
    def bench(self, *args: Any) -> None: pass


class FilelogSaver(Protocol):
    def save_log_from_tmp(self, tmp_logfile: str) -> None: pass

class FilelogManager(Protocol):
    def finalize(self) -> None: pass
    def set_local_repository(self, local_repository: FilelogSaver) -> None: pass

class FileLogger(Logger, FilelogManager):
    def __init__(self) -> None:
        self._logfile: Optional[TextIO] = cast(TextIO, tempfile.NamedTemporaryFile('w', delete=False))
        self._local_repository: Optional[FilelogSaver] = None

    def finalize(self) -> None:
        if self._logfile is None:
            return

        if self._local_repository is None:
            self.print('Log saved in temp file: ' + self._logfile.name)

        self._logfile.close()
        if self._local_repository is not None:
            self._local_repository.save_log_from_tmp(self._logfile.name)
        self._logfile = None

    def set_local_repository(self, local_repository: FilelogSaver) -> None:
        self._local_repository = local_repository

    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=True) -> None:
        self._do_print_in_file(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args: Any, sep: str='', end: str='\n', flush: bool=True) -> None:
        self._do_print_in_file("DEBUG| ", *_transform_debug_args(args), sep=sep, end=end, flush=flush)

    def bench(self, *args: Any) -> None:
        self._do_print_in_file(*args, sep='', end='\n', flush=False)

    def _do_print_in_file(self, *args: Any, sep: str, end: str, flush: bool) -> None:
        if self._logfile is not None:
            _do_print(*args, sep=sep, end=end, file=self._logfile, flush=flush)


class ConfigLogManager(Protocol):
    def configure(self, config: Config) -> None: pass

class TopLogger(Logger, ConfigLogManager):
    def __init__(self, print_logger: PrintLogger, file_logger: FileLogger) -> None:
        self.print_logger = print_logger
        self.file_logger = file_logger
        self._verbose_mode = True
        self._received_exception = False
        self._start_time: Optional[float] = None

    @staticmethod
    def for_main() -> 'TopLogger':
        return TopLogger(PrintLogger(), FileLogger())

    def configure(self, config: Config) -> None:
        if config['verbose']:
            self._start_time = config['start_time']
        else:
            self._verbose_mode = False

    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=False) -> None:
        self.print_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
        self.file_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
    def debug(self, *args: Any, sep: str='', end: str='\n', flush: bool=False) -> None:
        if self._verbose_mode is False and self._received_exception is False:
            if any(isinstance(a, BaseException) for a in args):
                self._received_exception = True
            else:
                return

        trans_args = _transform_debug_args(args)
        if self._verbose_mode:
            self.print_logger.debug(*trans_args, sep=sep, end=end, flush=flush)
        self.file_logger.debug(*trans_args, sep=sep, end=end, flush=flush)
    def bench(self, *args: Any) -> None:
        if self._start_time is None:
            return

        bench_header = f'BENCH {time_str(self._start_time)}| '
        self.print_logger.bench(bench_header, *args)
        self.file_logger.bench(bench_header, *args)

def _transform_debug_args(args: tuple[Any, ...]) -> list[str]:
    exception_msgs: list[str] = []
    rest_args: list[str] = []
    interp_count = 0
    interp_main = ''
    interp_subs: list[str] = []
    for a in args:
        if isinstance(a, Exception):
            exception_msgs.append(_format_ex(a))
            continue

        if interp_count > 1:
            interp_subs.append(str(a))
            interp_count -= 1
        elif interp_count == 1:
            try:
                rest_args.append(interp_main % (*interp_subs, str(a)))
            except Exception as e:
                exception_msgs.append(_format_ex(e))
                rest_args.extend([interp_main, *interp_subs, str(a)])
            interp_subs = []
            interp_count = 0
            interp_main = ''
        elif isinstance(a, str) and (interp_count := a.count('%s')) > 0:
            interp_main = a
        else:
            rest_args.append(str(a))
    return [*rest_args, *exception_msgs]

def _format_ex(e: BaseException) -> str:
    exception_msg = ''.join(traceback.TracebackException.from_exception(e).format())
    padding = ' ' * 4
    while e.__cause__ is not None:
        e = e.__cause__
        exception_msg += padding + 'CAUSE: ' + padding.join(traceback.TracebackException.from_exception(e).format())
        padding += ' ' * 4
    return exception_msg


class DebugOnlyLoggerDecorator(Logger):
    def __init__(self, decorated_logger: Logger) -> None:
        self._decorated_logger = decorated_logger

    def print(self, *args: Any, sep: str='', end: str='\n', file: TextIO=sys.stdout, flush: bool=True) -> None:
        """Calls debug instead of print"""
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args: Any, sep: str='', end: str='\n', flush: bool=True) -> None:
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def bench(self, *args: Any) -> None:
        self._decorated_logger.bench(*args)

def time_str(start_time: float) -> str:
    return str(datetime.timedelta(seconds=time.monotonic() - start_time))[0:-3]
