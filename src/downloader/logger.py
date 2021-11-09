# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import tempfile
import sys
from abc import ABC, abstractmethod


class Logger(ABC):
    @abstractmethod
    def set_local_repository(self, local_repository):
        """"can find where to store anything after this method is called"""

    @abstractmethod
    def enable_verbose_mode(self):
        """makes logs more verbose"""

    @abstractmethod
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        """print always"""

    @abstractmethod
    def debug(self, *args, sep='', end='\n', flush=True):
        """print only to debug target"""


class FileLogger(Logger):
    def __init__(self):
        self._logfile = tempfile.NamedTemporaryFile('w', delete=False)
        self._local_repository = None
        self._verbose_mode = False

    def enable_verbose_mode(self):
        self._verbose_mode = True

    def set_local_repository(self, local_repository):
        self._local_repository = local_repository

    def close_logfile(self):
        if self._local_repository is not None:
            self._logfile.close()
            self._local_repository.save_log_from_tmp(self._logfile.name)
            self._logfile = None
            self._local_repository = None

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        if not self._verbose_mode:
            self._do_print(*args, sep=sep, end=end, file=file, flush=flush)
        self.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        if self._logfile is not None:
            self._do_print(*args, sep=sep, end=end, file=self._logfile, flush=flush)
        if self._verbose_mode:
            self._do_print(*args, sep=sep, end=end, file=sys.stdout, flush=flush)

    @staticmethod
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


class SilentLogger(Logger):

    def __init__(self, decorated_logger):
        self._decorated_logger = decorated_logger

    def set_local_repository(self, local_repository):
        self._decorated_logger.set_local_repository(local_repository)

    def enable_verbose_mode(self):
        self._decorated_logger.enable_verbose_mode()

    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)

    def debug(self, *args, sep='', end='\n', flush=True):
        self._decorated_logger.debug(*args, sep=sep, end=end, flush=flush)
