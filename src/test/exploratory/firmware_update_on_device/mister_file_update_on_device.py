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

import json
from src.debug import exec_ssh, store_pull, store_push, run_build, chdir_root


def main():
    store_pull()
    with open('downloader.json', 'r') as f: downloader_json = json.load(f)
    downloader_json['dbs']['distribution_mister']['files']['MiSTer']['hash'] = ''
    downloader_json['dbs']['distribution_mister']['files']['MiSTer']['size'] = 0
    with open('downloader.json', 'w') as f: json.dump(downloader_json, f)
    store_push()
    exec_ssh('cd /media/fat; rm -f MiSTer; touch MiSTer')
    run_build()


if __name__ == '__main__':
    chdir_root()
    main()
