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

import os
from downloader.main import main
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, DEFAULT_CURL_SSL_OPTIONS, \
    KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, KENV_CURL_SSL, KENV_COMMIT, KENV_ALLOW_REBOOT, \
    KENV_UPDATE_LINUX, KENV_DEFAULT_DB_URL, \
    KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, KENV_DEBUG, KENV_FAIL_ON_FILE_ERROR, KENV_LOGFILE, KENV_PC_LAUNCHER

if __name__ == '__main__':
    exit_code = main({
        KENV_DOWNLOADER_LAUNCHER_PATH: os.getenv(KENV_DOWNLOADER_LAUNCHER_PATH, None),
        KENV_DOWNLOADER_INI_PATH: os.getenv(KENV_DOWNLOADER_INI_PATH, None),
        KENV_LOGFILE: os.getenv(KENV_LOGFILE, None),
        KENV_CURL_SSL: os.getenv(KENV_CURL_SSL, DEFAULT_CURL_SSL_OPTIONS),
        KENV_COMMIT: os.getenv(KENV_COMMIT, 'unknown'),
        KENV_ALLOW_REBOOT: os.getenv(KENV_ALLOW_REBOOT, None),
        KENV_UPDATE_LINUX: os.getenv(KENV_UPDATE_LINUX, 'true').lower(),
        KENV_DEFAULT_DB_URL: os.getenv(KENV_DEFAULT_DB_URL, DISTRIBUTION_MISTER_DB_URL),
        KENV_DEFAULT_DB_ID: os.getenv(KENV_DEFAULT_DB_ID, DISTRIBUTION_MISTER_DB_ID),
        KENV_DEFAULT_BASE_PATH: os.getenv(KENV_DEFAULT_BASE_PATH, None),
        KENV_PC_LAUNCHER: os.getenv(KENV_PC_LAUNCHER, None),
        KENV_DEBUG: os.getenv(KENV_DEBUG, 'false').lower(),
        KENV_FAIL_ON_FILE_ERROR: os.getenv(KENV_FAIL_ON_FILE_ERROR, 'false')
    })

    exit(exit_code)
