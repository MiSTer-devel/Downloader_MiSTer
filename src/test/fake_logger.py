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

import sys
from downloader.logger import Logger


class NoLogger(Logger):
    def print(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        pass

    def debug(self, *args, sep='', end='\n', file=sys.stdout, flush=False):
        pass

    def set_local_repository(self, local_repository):
        pass

    def enable_verbose_mode(self):
        pass
