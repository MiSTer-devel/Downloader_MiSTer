#!/usr/bin/env python3
# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
import os
import locale
import argparse
from pathlib import Path
from typing import Optional

from downloader.config import Config, Environment, InvalidConfigParameter, default_config
from downloader.config_reader import ConfigReader
from downloader.constants import KENV_LOGLEVEL, KENV_DOWNLOADER_OUTPUT, KENV_LC_HTTP_PROXY, KENV_HTTP_PROXY, KENV_HTTPS_PROXY, \
    KENV_LC_HTTPS_PROXY, KENV_ROTATE_LOGS, KENV_SKIP_FREE_SPACE_CHECKS, DOWNLOADER_OUTPUT_HUMAN, K_DOWNLOADER_OUTPUT, \
    DOWNLOADER_VERSION
from downloader.logger import OffLogger, TopLogger
from downloader.full_run_service_factory import FullRunServiceFactory
from downloader.update_output import update_output_for_mode


def main(env: Environment, start_time: float) -> int:
    # This function should be called in __main__.py which just bootstraps the application.
    # It should receive an 'env' dictionary produced by calling the "read_env" function below.

    locale.setlocale(locale.LC_CTYPE, "")
    config_reader = ConfigReader(OffLogger(), env, start_time)
    config = default_config()
    config_reader.read_initial_env(config)
    logger = TopLogger.for_main(config, start_time)
    update_output = update_output_for_mode(config[K_DOWNLOADER_OUTPUT], logger)
    config_reader.set_logger(logger)
    logger.bench('MAIN start.')

    # noinspection PyBroadException
    try:
        config_path = config_reader.calculate_config_path(str(Path().resolve()))
        config_reader.read_rest_env_and_config_file(config_path, config)
        exit_code = execute_full_run(
            FullRunServiceFactory.for_main(logger, update_output),
            sys.argv,
            config
        )
    except InvalidConfigParameter as e:
        logger.debug(e)
        update_output.error('config', 'Configuration error: %s' % str(e))
        exit_code = 1
    except Exception as _:
        import traceback
        update_output.error('unexpected')
        logger.print(traceback.format_exc())
        exit_code = 1
    finally:
        logger.bench('MAIN end.')
        logger.file_logger.finalize()

    return exit_code


def read_env(default_commit: Optional[str]) -> Environment:
    # The default_commit should be coming from the commit.py file which is produced by the building process.
    # It's not under version control, so if it's not present, it will come as "None".
    from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, DEFAULT_CURL_SSL_OPTIONS, \
    KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, KENV_EXTRA_DROP_IN_DATABASE_FILES, KENV_CURL_SSL, KENV_COMMIT, KENV_ALLOW_REBOOT, \
    KENV_UPDATE_LINUX, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, KENV_DEBUG, \
    KENV_FAIL_ON_FILE_ERROR, KENV_LOGFILE, KENV_PC_LAUNCHER, DEFAULT_UPDATE_LINUX_ENV, KENV_FORCED_BASE_PATH, \
    KENV_SSL_CERT_FILE
    return {
        'DOWNLOADER_LAUNCHER_PATH': os.getenv(KENV_DOWNLOADER_LAUNCHER_PATH, None),
        'DOWNLOADER_INI_PATH': os.getenv(KENV_DOWNLOADER_INI_PATH, None),
        'EXTRA_DROP_IN_DATABASE_FILES': os.getenv(KENV_EXTRA_DROP_IN_DATABASE_FILES, ''),
        'LOGFILE': os.getenv(KENV_LOGFILE, None),
        'LOGLEVEL': os.getenv(KENV_LOGLEVEL, '').lower(),  # info | debug, http
        'DOWNLOADER_OUTPUT': os.getenv(KENV_DOWNLOADER_OUTPUT, DOWNLOADER_OUTPUT_HUMAN).lower(),
        'CURL_SSL': os.getenv(KENV_CURL_SSL, DEFAULT_CURL_SSL_OPTIONS),
        'COMMIT': os.getenv(KENV_COMMIT, default_commit or 'unknown'),
        'ALLOW_REBOOT': os.getenv(KENV_ALLOW_REBOOT, None),
        'UPDATE_LINUX': os.getenv(KENV_UPDATE_LINUX, DEFAULT_UPDATE_LINUX_ENV).lower(),
        'DEFAULT_DB_URL': os.getenv(KENV_DEFAULT_DB_URL, DISTRIBUTION_MISTER_DB_URL),
        'DEFAULT_DB_ID': os.getenv(KENV_DEFAULT_DB_ID, DISTRIBUTION_MISTER_DB_ID),
        'DEFAULT_BASE_PATH': os.getenv(KENV_DEFAULT_BASE_PATH, None),
        'FORCED_BASE_PATH': os.getenv(KENV_FORCED_BASE_PATH, None),
        'PC_LAUNCHER': os.getenv(KENV_PC_LAUNCHER, None),
        'SKIP_FREE_SPACE_CHECKS': os.getenv(KENV_SKIP_FREE_SPACE_CHECKS, None),
        'DEBUG': os.getenv(KENV_DEBUG, 'false').lower(),
        'FAIL_ON_FILE_ERROR': os.getenv(KENV_FAIL_ON_FILE_ERROR, 'false'),
        'HTTP_PROXY': os.getenv(KENV_HTTP_PROXY) or os.getenv(KENV_LC_HTTP_PROXY) or '',
        'HTTPS_PROXY': os.getenv(KENV_HTTPS_PROXY) or os.getenv(KENV_LC_HTTPS_PROXY) or '',
        'ROTATE_LOGS': os.getenv(KENV_ROTATE_LOGS, 'true').lower(),
        'SSL_CERT_FILE': os.getenv(KENV_SSL_CERT_FILE, '')
    }


def execute_full_run(full_run_service_factory: FullRunServiceFactory, argv, config: Config) -> int:
    # The factory instance is just creating the components of the system and passing the appropriate
    # dependencies to each one. Check directly full_run_service.py to see the program execution flow.
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    if args.command == 'version':
        print(DOWNLOADER_VERSION)
        return 0

    runner = full_run_service_factory.create(config)
    if args.command == 'print_drives':
        exit_code = runner.print_drives()
    else:
        # The heart of this execution is the method "download_dbs_contents" in online_importer.py
        exit_code = runner.full_run()

    return exit_code


def _parse_args(argv):
    prog = Path(argv[0]).name if len(argv) > 0 and argv[0] else 'downloader.sh'
    parser = argparse.ArgumentParser(prog=prog, add_help=False, allow_abbrev=False)
    parser.set_defaults(command='full_run')
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument('--full-run', '-fr', action='store_const', const='full_run', dest='command', help='run Downloader')
    commands.add_argument('--print-drives', '-pd', action='store_const', const='print_drives', dest='command', help='print detected external drives and exit')
    commands.add_argument('--version', '-v', action='store_const', const='version', dest='command', help='print Downloader version and exit')
    return parser.parse_args(argv[1:] if len(argv) > 0 else [])
