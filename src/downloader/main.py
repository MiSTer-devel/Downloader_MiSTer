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

import traceback
import sys
import os
from pathlib import Path
from typing import Optional

from downloader.config import Environment
from downloader.config_reader import ConfigReader
from downloader.constants import KENV_LOGLEVEL
from downloader.logger import FileLoggerDecorator, PrintLogger
from downloader.full_run_service_factory import FullRunServiceFactory


def main(env: Environment) -> int:
    # This function should be called in __main__.py which just bootstraps the application.
    # It should receive an 'env' dictionary produced by calling the "read_env" function below.

    printer = PrintLogger()
    logger = FileLoggerDecorator(printer)
    # noinspection PyBroadException
    try:
        exit_code = execute_full_run(
            FullRunServiceFactory.for_main(logger, printer),
            ConfigReader(logger, env),
            sys.argv
        )
    except Exception as _:
        logger.print(traceback.format_exc())
        exit_code = 1

    logger.finalize()
    return exit_code


def read_env(default_commit: Optional[str]) -> Environment:
    # The default_commit should be coming from the commit.py file which is produced by the building process.
    # It's not under version control, so if it's not present, it will come as "None".
    from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, DEFAULT_CURL_SSL_OPTIONS, \
    KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, KENV_CURL_SSL, KENV_COMMIT, KENV_ALLOW_REBOOT, \
    KENV_UPDATE_LINUX, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, KENV_DEBUG, \
    KENV_FAIL_ON_FILE_ERROR, KENV_LOGFILE, KENV_PC_LAUNCHER, DEFAULT_UPDATE_LINUX_ENV, KENV_FORCED_BASE_PATH
    return {
        'DOWNLOADER_LAUNCHER_PATH': os.getenv(KENV_DOWNLOADER_LAUNCHER_PATH, None),
        'DOWNLOADER_INI_PATH': os.getenv(KENV_DOWNLOADER_INI_PATH, None),
        'LOGFILE': os.getenv(KENV_LOGFILE, None),
        'LOGLEVEL': os.getenv(KENV_LOGLEVEL, '').lower(),  # info | debug, http
        'CURL_SSL': os.getenv(KENV_CURL_SSL, DEFAULT_CURL_SSL_OPTIONS),
        'COMMIT': os.getenv(KENV_COMMIT, default_commit or 'unknown'),
        'ALLOW_REBOOT': os.getenv(KENV_ALLOW_REBOOT, None),
        'UPDATE_LINUX': os.getenv(KENV_UPDATE_LINUX, DEFAULT_UPDATE_LINUX_ENV).lower(),
        'DEFAULT_DB_URL': os.getenv(KENV_DEFAULT_DB_URL, DISTRIBUTION_MISTER_DB_URL),
        'DEFAULT_DB_ID': os.getenv(KENV_DEFAULT_DB_ID, DISTRIBUTION_MISTER_DB_ID),
        'DEFAULT_BASE_PATH': os.getenv(KENV_DEFAULT_BASE_PATH, None),
        'FORCED_BASE_PATH': os.getenv(KENV_FORCED_BASE_PATH, None),
        'PC_LAUNCHER': os.getenv(KENV_PC_LAUNCHER, None),
        'DEBUG': os.getenv(KENV_DEBUG, 'false').lower(),
        'FAIL_ON_FILE_ERROR': os.getenv(KENV_FAIL_ON_FILE_ERROR, 'false'),
    }


def execute_full_run(full_run_service_factory: FullRunServiceFactory, config_reader: ConfigReader, argv) -> int:
    # The config will merge env inputs and 'downloader.ini' inputs, representing all configurable inputs.
    config = config_reader.read_config(config_reader.calculate_config_path(str(Path().resolve())))

    # The factory instance is just creating the components of the system and passing the appropriate
    # dependencies to each one. Check directly full_run_service.py to see the program execution flow.
    runner = full_run_service_factory.create(config)
    if len(argv) == 2 and (argv[1] == '--print-drives' or argv[1] == '-pd'):
        exit_code = runner.print_drives()
    else:
        # The heart of this execution is the method "download_dbs_contents" in online_importer.py
        exit_code = runner.full_run()

    return exit_code
