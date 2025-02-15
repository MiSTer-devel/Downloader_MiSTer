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
import tempfile
import sys
import time
import traceback
from typing import Any, List, Optional, Protocol

from downloader.config import Config


class Logger(Protocol):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True) -> None: """print always"""
    def debug(self, *args, sep='', end='\n', flush=True) -> None: """print only to debug target"""
    def bench(self, *args) -> None: """print only to debug target"""


class PrintLogger(Logger):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        _do_print(*args, sep=sep, end=end, file=file, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        _do_print("DEBUG| ", *args, sep=sep, end=end, file=sys.stdout, flush=flush)

    def bench(self, *args):
        _do_print(*args, sep='', end='\n', file=sys.stdout, flush=True)


class OffLogger(Logger):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False): pass
    def bench(self, *args): pass

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

class FileLogger(Logger, FilelogManager):
    def __init__(self):
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
        self._do_print_in_file(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._do_print_in_file("DEBUG| ", *_transform_debug_args(args), sep=sep, end=end, flush=flush)

    def bench(self, *args):
        self._do_print_in_file(*args, sep='', end='\n', flush=False)

    def _do_print_in_file(self, *args, sep, end, flush):
        if self._logfile is not None:
            _do_print(*args, sep=sep, end=end, file=self._logfile, flush=flush)



class ConfigLogManager(Protocol):
    def configure(self, config: Config) -> None: pass


class TopLogger(Logger, ConfigLogManager):
    def __init__(self, print_logger: PrintLogger, file_logger: FileLogger):
        self.print_logger = print_logger
        self.file_logger = file_logger
        self._verbose_mode = True
        self._debug = True
        self._start_time = None

    @staticmethod
    def for_main():
        return TopLogger(PrintLogger(), FileLogger())

    def configure(self, config: Config):
        if config['verbose']:
            self._start_time = config['start_time']
        else:
            self._verbose_mode = False

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        self.print_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
        self.file_logger.print(*args, sep=sep, end=end, file=file, flush=flush)
    def debug(self, *args, sep='', end='\n', flush=False):
        if self._debug is False:
            return

        args = _transform_debug_args(args)
        if self._verbose_mode:
            self.print_logger.debug(*args, sep=sep, end=end, flush=flush)
        self.file_logger.debug(*args, sep=sep, end=end, flush=flush)
    def bench(self, *args):
        if self._start_time is None:
            return

        time_str = str(datetime.timedelta(seconds=time.time() - self._start_time))[0:-4]
        bench_header = f'BENCH {time_str}| '
        self.print_logger.bench(bench_header, *args)
        self.file_logger.bench(bench_header, *args)


def _transform_debug_args(args: List[Any]) -> List[str]:
    exception_msgs = []
    rest_args = []
    interp_count = 0
    interp_main = ''
    interp_subs = []
    for a in args:
        if isinstance(a, Exception):
            exception_msgs.append(_format_ex(a))
            continue

        if interp_count > 1:
            interp_subs.append(str(a))
            interp_count =- 1
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

def _format_ex(e: Exception) -> str:
    exception_msg = ''.join(traceback.TracebackException.from_exception(e).format())
    padding = ' ' * 4
    while e.__cause__ is not None:
        e = e.__cause__
        exception_msg += padding + 'CAUSE: ' + padding.join(traceback.TracebackException.from_exception(e).format())
        padding += ' ' * 4
    return exception_msg


class DebugOnlyLoggerDecorator(Logger):
    def __init__(self, decorated_logger: Logger):
        self._decorated_logger = decorated_logger

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """Calls debug instead of print"""
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def bench(self, *args):
        self._decorated_logger.bench(*args)
