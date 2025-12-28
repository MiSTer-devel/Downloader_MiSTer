#!/usr/bin/env python3
# Copyright (c) 2022-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from shutil import copy, copyfileobj
from tempfile import NamedTemporaryFile
from urllib.request import urlopen


def fetch_temp_downloader():
    downloader_source = os.environ.get('DOWNLOADER_SOURCE', 'https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/downloader.zip')

    with NamedTemporaryFile(suffix='.zip', mode='wb', delete=False) as temp:
        temp_name = temp.name

        if downloader_source.startswith('http://') or downloader_source.startswith('https://'):
            with urlopen(downloader_source) as in_stream:
                if in_stream.status == 200:
                    copyfileobj(in_stream, temp)
        else:
            temp.close()
            copy(downloader_source, temp_name)

    return temp_name


def launch_downloader(filename):
    env = os.environ.copy()
    env['PC_LAUNCHER'] = os.path.realpath(__file__)
    return subprocess.run(['python3', filename], env=env, stderr=subprocess.STDOUT).returncode


def main():
    temp_filename = None
    try:
        temp_filename = fetch_temp_downloader()
        result = launch_downloader(temp_filename)
    except Exception as e:
        print(e)
        result = 1

    if temp_filename:
        try:
            os.unlink(temp_filename)
        except FileNotFoundError:
            pass

    if os.environ.get('PC_LAUNCHER_NO_WAIT') != '1':
        input("Press Enter to continue...")

    return result


if __name__ == '__main__':
    exit(main())
