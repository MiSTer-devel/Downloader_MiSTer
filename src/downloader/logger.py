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
from abc import abstractmethod, ABC
from typing import List, Any

from downloader.config import Config


class Logger(ABC):
    @abstractmethod
    def configure(self, config: Config):
        """makes logs more verbose"""

    @abstractmethod
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """print always"""

    @abstractmethod
    def debug(self, *args, sep='', end='\n', flush=True):
        """print only to debug target"""

    @abstractmethod
    def bench(self, label: str):
        """print only to debug target"""

    def finalize(self):
        """to be called at the very end, should not call any method after this one"""


class PrintLogger(Logger):
    @staticmethod
    def make_configured(config: Config):
        logger = PrintLogger()
        logger.configure(config)
        return logger

    def __init__(self):
        self._verbose_mode = False
        self._start_time = None
        self._describe_now = False

    def configure(self, config: Config):
        if config['verbose']:
            self._verbose_mode = True
            self._start_time = config['start_time']

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        self._do_print(*args, sep=sep, end=end, file=file, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        if self._verbose_mode:
            exceptions = []
            for a in args:
                if isinstance(a, Exception):
                    exceptions.append(a)
            if len(exceptions) > 0:
                args = list(set(args) - set(exceptions))
                for e in exceptions:
                    self._do_print("".join(traceback.format_exception(type(e), e, e.__traceback__)), sep=sep, end=end, file=sys.stdout, flush=flush)
            self._do_print(*args, sep=sep, end=end, file=sys.stdout, flush=flush)

    def bench(self, label: str):
        if self._start_time is not None:
            self._do_print('%s| %s' % (str(datetime.timedelta(seconds=time.time() - self._start_time))[0:-4], label), sep='', end='\n', file=sys.stdout, flush=True)

    def finalize(self):
        pass

    def _do_print(self, *args, sep, end, file, flush):
        try:
            print(*args, sep=sep, end=end, file=file, flush=flush)
        except UnicodeEncodeError:
            pack = []
            for a in args:
                pack.append(a.encode('utf8', 'surrogateescape'))
            print(*pack, sep=sep, end=end, file=file, flush=flush)
        except BaseException as error:
            print('An unknown exception occurred during logging: %s' % str(error))


class NoLogger(Logger):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        pass

    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        pass

    def bench(self, label: str):
        pass

    def configure(self, config: Config):
        pass

    def finalize(self):
        pass


class FileLoggerDecorator(Logger):
    def __init__(self, decorated_logger: Logger, local_repository_provider):
        self._decorated_logger = decorated_logger
        self._logfile = tempfile.NamedTemporaryFile('w', delete=False)
        self._local_repository_provider = local_repository_provider

    def configure(self, config: Config):
        self._decorated_logger.configure(config)

    def finalize(self):
        self._decorated_logger.finalize()
        if self._logfile is None:
            return

        self._logfile.close()
        self._local_repository_provider.local_repository.save_log_from_tmp(self._logfile.name)
        self._logfile = None

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

    def configure(self, config: Config):
        self._decorated_logger.configure(config)

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """Calls debug instead of print"""
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def bench(self, label: str):
        self._decorated_logger.bench(label)

    def finalize(self):
        self._decorated_logger.finalize()


# @TODO: Consider moving this one to test code
class DescribeNowDecorator(Logger):
    def __init__(self, decorated_logger: Logger):
        self._re = re.compile(r'^ */[^:]+:\d+.*$')  # Matches paths such as /asd/bef/df:34
        self._decorated_logger = decorated_logger

    def configure(self, config: Config): self._decorated_logger.configure(config)
    def bench(self, label: str): self._decorated_logger.bench(label)
    def finalize(self): self._decorated_logger.finalize()

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
