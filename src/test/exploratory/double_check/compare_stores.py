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
import subprocess
import sys
import difflib


def main():
    if len(sys.argv) != 3:
        print('Not enough arguments: %d' % len(sys.argv))
        return -1

    db1 = load_store(sys.argv[1])
    db2 = load_store(sys.argv[2])

    if db1 == db2:
        print('Files are the same.')
        return 0

    print('Found differences!')
    print()

    for line in difflib.unified_diff(db1.splitlines(), db2.splitlines()):
        print(line)

    return -1


def clean_store(db):
    for store in db['dbs'].values():
        store['timestamp'] = 0
        store['base_path'] = ''


def load_store(store_path):
    result = subprocess.run(['unzip', '-p', store_path], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception('Could not load "%s"!' % store_path)

    return json.dumps(clean_store(json.loads(result.stdout.decode())), sort_keys=True, indent=4)


if __name__ == '__main__':
    exit(main())
