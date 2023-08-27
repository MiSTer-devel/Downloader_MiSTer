#!/usr/bin/env python3
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

"""
On the root of the project, follow these steps:

Call the command ./src/debug.sh store pull
open the file downloader.json
modify json['files']['MiSTer']['hash'] to be ''
modify json['files']['MiSTer']['size'] to be 0
save the json at downloader.json
Call the command ./src/debug.sh store push
Call the command ./src/debug.sh touch MiSTer
Call the command ./src/debug.sh run
"""

import subprocess
import json
from os import chdir


def main():
    subprocess.run(['./src/debug.sh', 'store', 'pull'])
    with open('downloader.json', 'r') as f:
        downloader_json = json.load(f)
    downloader_json['dbs']['distribution_mister']['files']['MiSTer']['hash'] = ''
    downloader_json['dbs']['distribution_mister']['files']['MiSTer']['size'] = 0
    with open('downloader.json', 'w') as f:
        json.dump(downloader_json, f)
    subprocess.run(['./src/debug.sh', 'store', 'push'])
    subprocess.run(['./src/debug.sh', 'touch', 'MiSTer'])
    subprocess.run(['./src/debug.sh', 'run'])


if __name__ == '__main__':
    chdir('../../../..')
    main()
