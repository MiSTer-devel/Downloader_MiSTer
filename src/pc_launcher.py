#!/usr/bin/env python3
# Copyright (c) 2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import os
import subprocess
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from urllib.request import urlopen


temp_container = {}


def fetch_temp_downloader():
    with NamedTemporaryFile(suffix='.zip', mode='wb', delete=False) as temp:
        temp_container['downloader'] = temp
        with urlopen('https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/downloader.zip') as in_stream:
            if in_stream.status == 200:
                copyfileobj(in_stream, temp)


def launch_downloader(filename):
    env = os.environ.copy()
    env['PC_LAUNCHER'] = os.path.realpath(__file__)
    return subprocess.run(['python3', filename], env=env, stderr=subprocess.STDOUT).returncode


def main():
    try:
        fetch_temp_downloader()
        result = launch_downloader(temp_container['downloader'].name)
    except Exception as e:
        print(e)
        result = 1

    if 'downloader' in temp_container:
        try:
            os.unlink(temp_container['downloader'].name)
        except FileNotFoundError:
            pass

    input("Press Enter to continue...")

    return result


if __name__ == '__main__':
    exit(main())
