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
from downloader.constants import KENV_LOGLEVEL, KENV_DOWNLOADER_OUTPUT, KENV_LC_HTTP_PROXY, KENV_HTTP_PROXY, \
    KENV_HTTPS_PROXY, KENV_LC_HTTPS_PROXY, KENV_ROTATE_LOGS, KENV_SKIP_FREE_SPACE_CHECKS, DOWNLOADER_OUTPUT_HUMAN, \
    K_DOWNLOADER_OUTPUT
from downloader.logger import OffLogger, TopLogger
from downloader.update_output import UpdateOutput, update_output_for_mode

_UTF8_RELAUNCH_ATTEMPTED_ENV = '_DOWNLOADER_UTF8_RELAUNCH_ATTEMPTED'


def main(env: Environment, start_time: float, argv=None) -> int:
    # This function should be called in __main__.py which just bootstraps the application.
    # It should receive an 'env' dictionary produced by calling the "read_env" function below.

    locale.setlocale(locale.LC_CTYPE, "")
    argv = sys.argv if argv is None else argv
    try:
        args = parse_args(argv)
    except SystemExit:
        return 1

    if args.command == 'version':
        from downloader.version_service import VersionService
        return VersionService().print_version(env['RELEASE_PATCH'])

    config_reader = ConfigReader(OffLogger(), env, start_time)
    config = default_config()
    config_reader.read_initial_env(config)
    is_print_only_command = args.command == 'check' or args.command == 'list_dbs'
    logger = TopLogger.for_print_only(config, start_time) \
        if is_print_only_command else TopLogger.for_main(config, start_time)
    update_output = update_output_for_mode(config[K_DOWNLOADER_OUTPUT], logger)
    config_reader.set_logger(logger)
    logger.bench('MAIN start.')

    # noinspection PyBroadException
    try:
        config_path = config_reader.calculate_config_path(str(Path().resolve()))
        config_reader.read_rest_env_and_config_file(config_path, config)
        exit_code = execute_command(args, config, logger, update_output)
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
        if not is_print_only_command:
            logger.bench('MAIN end.')
        logger.file_logger.finalize()

    return exit_code


def execute_command(args, config: Config, logger: TopLogger, update_output: UpdateOutput) -> int:
    if args.command == 'check':
        from downloader.check_service_factory import CheckServiceFactory
        check_service = CheckServiceFactory.for_main(logger, update_output).create(config)
        return check_service.check_available_updates(args.check_db_ids)
    if args.command == 'uninstall':
        from downloader.uninstall_service_factory import UninstallServiceFactory
        uninstall_service = UninstallServiceFactory.for_main(logger, update_output).create(config)
        return uninstall_service.uninstall(args.uninstall_db_ids, args.force)
    if args.command == 'list_dbs':
        from downloader.list_dbs_service import ListDbsService
        return ListDbsService(update_output).list_dbs(config)
    if args.command == 'print_drives':
        from downloader.full_run_service_factory import FullRunServiceFactory
        runner = FullRunServiceFactory.for_main(logger, update_output).create(config)
        return runner.print_drives()
    if args.command == 'run_only':
        from downloader.full_run_service_factory import FullRunServiceFactory
        runner = FullRunServiceFactory.for_main(logger, update_output).create(config)
        return runner.run_only(args.run_only_db_ids)

    from downloader.full_run_service_factory import FullRunServiceFactory
    runner = FullRunServiceFactory.for_main(logger, update_output).create(config)
    # The heart of this execution is the method "download_dbs_contents" in online_importer.py.
    return runner.full_run()


def ensure_utf8_filesystem_encoding() -> None:
    # Filesystem encoding is fixed at startup. Relaunch source builds for non-ASCII paths;
    # Nuitka enables UTF-8 Mode at build time and must not relaunch itself.
    if os.name == 'nt' or sys.flags.utf8_mode != 0 or not sys.executable:
        return
    if getattr(sys, 'frozen', False) or hasattr(sys.modules['__main__'], '__compiled__'):
        return
    if sys.getfilesystemencoding().lower() in ('utf-8', 'utf8'):
        return
    # Avoid looping if the replacement ignored -X utf8.
    if os.getenv(_UTF8_RELAUNCH_ATTEMPTED_ENV) == '1':
        print('WARNING! Restarting Downloader did not enable UTF-8 Mode. Continuing without it.',
              file=sys.stderr, flush=True)
        return

    relaunch_env = os.environ.copy()
    relaunch_env[_UTF8_RELAUNCH_ATTEMPTED_ENV] = '1'
    try:
        os.execve(sys.executable, [sys.executable, '-X', 'utf8', *sys.argv], relaunch_env)
    except OSError as error:
        # Relaunching is best effort; the normal run must continue.
        print('WARNING! Could not restart Downloader in UTF-8 Mode: %s. Continuing without it.' % error,
              file=sys.stderr, flush=True)


def read_env(default_commit: Optional[str], default_release_patch: Optional[int] = None) -> Environment:
    # The defaults should be coming from the commit.py file which is produced by the building process.
    # It's not under version control, so if it's not present, they will come as "None".
    from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, \
        DEFAULT_CURL_SSL_OPTIONS, KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, \
        KENV_EXTRA_DROP_IN_DATABASE_FILES, KENV_CURL_SSL, KENV_COMMIT, KENV_ALLOW_REBOOT, KENV_UPDATE_LINUX, \
        KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, KENV_DEBUG, KENV_FAIL_ON_FILE_ERROR, \
        KENV_LOGFILE, KENV_PC_LAUNCHER, DEFAULT_UPDATE_LINUX_ENV, KENV_FORCED_BASE_PATH, KENV_SSL_CERT_FILE
    return {
        'DOWNLOADER_LAUNCHER_PATH': os.getenv(KENV_DOWNLOADER_LAUNCHER_PATH, None),
        'DOWNLOADER_INI_PATH': os.getenv(KENV_DOWNLOADER_INI_PATH, None),
        'EXTRA_DROP_IN_DATABASE_FILES': os.getenv(KENV_EXTRA_DROP_IN_DATABASE_FILES, ''),
        'LOGFILE': os.getenv(KENV_LOGFILE, None),
        'LOGLEVEL': os.getenv(KENV_LOGLEVEL, '').lower(),  # info | debug, http
        'DOWNLOADER_OUTPUT': os.getenv(KENV_DOWNLOADER_OUTPUT, DOWNLOADER_OUTPUT_HUMAN).lower(),
        'CURL_SSL': os.getenv(KENV_CURL_SSL, DEFAULT_CURL_SSL_OPTIONS),
        'COMMIT': os.getenv(KENV_COMMIT, default_commit or 'unknown'),
        'RELEASE_PATCH': default_release_patch,
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


def parse_args(argv):
    prog = Path(argv[0]).name if len(argv) > 0 and argv[0] else 'downloader.sh'
    parser = argparse.ArgumentParser(prog=prog, add_help=False, allow_abbrev=False)
    parser.set_defaults(command='full_run')
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument('--full-run', '-fr', action='store_const', const='full_run', dest='command',
                          help='run Downloader')
    commands.add_argument('--print-drives', '-pd', action='store_const', const='print_drives', dest='command',
                          help='print detected external drives and exit')
    commands.add_argument('--check', '-c', nargs='*', dest='check_db_ids', metavar='DB_ID',
                          help='check for available updates and exit')
    commands.add_argument('--run-only', nargs='+', dest='run_only_db_ids',
                          help='run Downloader only for the listed database IDs')
    commands.add_argument('--uninstall', nargs='+', dest='uninstall_db_ids', metavar='DB_ID',
                          help='uninstall the listed databases')
    commands.add_argument('--list-dbs', action='store_const', const='list_dbs', dest='command',
                          help='list configured database IDs and exit')
    commands.add_argument('--version', '-v', action='store_const', const='version', dest='command',
                          help='print Downloader version and exit')
    parser.add_argument('--force', action='store_true', help='accept unverifiable external content during uninstall')
    args = [arg for arg in (argv[1:] if len(argv) > 0 else []) if arg != '']
    parsed_args = parser.parse_args(args)
    if parsed_args.check_db_ids is not None:
        parsed_args.command = 'check'
    elif parsed_args.run_only_db_ids is not None:
        parsed_args.command = 'run_only'
    elif parsed_args.uninstall_db_ids is not None:
        parsed_args.command = 'uninstall'
    if parsed_args.force and parsed_args.command != 'uninstall':
        parser.error('--force requires --uninstall')
    return parsed_args
