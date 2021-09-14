#!/usr/bin/env python3
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

import os
from downloader.main import main

if __name__ == '__main__':
    exit_code = main({
        'DOWNLOADER_LAUNCHER_PATH': os.getenv('DOWNLOADER_LAUNCHER_PATH', None),
        'CURL_SSL': os.getenv('CURL_SSL', '--cacert /etc/ssl/certs/cacert.pem'),
        'COMMIT': os.getenv('COMMIT', 'unknown'),
        'ALLOW_REBOOT': os.getenv('ALLOW_REBOOT', None),
        'UPDATE_LINUX': os.getenv('UPDATE_LINUX', 'true'),
        'DEFAULT_DB_URL': os.getenv('DEFAULT_DB_URL', 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip'),
        'DEFAULT_DB_ID': os.getenv('DEFAULT_DB_ID', 'distribution_mister')
    })

    exit(exit_code)
