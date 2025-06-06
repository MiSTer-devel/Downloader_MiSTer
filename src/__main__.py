#!/usr/bin/env python3
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

import time
start_time = time.monotonic()

from sys import exit

try:
    from downloader.main import main, read_env
except (ImportError, SyntaxError) as e:
    print(e)
    print('\n')
    print('Warning! Your OS version seems to be older than September 2021!')
    print('Please upgrade your OS before running Downloader')
    print('More info at https://github.com/MiSTer-devel/mr-fusion')
    print()
    exit(10)  # Same exit value as: downloader.constants.EXIT_ERROR_WRONG_SETUP

try:
    from commit import default_commit  # type: ignore[import-not-found]
except ImportError as e:
    default_commit = None  # type: ignore[assignment]

if __name__ == '__main__':
    exit_code = main(read_env(default_commit), start_time)
    exit(exit_code)
