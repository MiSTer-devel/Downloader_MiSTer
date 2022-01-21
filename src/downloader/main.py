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

import time
import subprocess
import traceback
import sys

from downloader.config import config_file_path
from downloader.logger import FileLogger
from downloader.full_run_service_factory import make_full_run_service


def main(env):
    logger = FileLogger()
    # noinspection PyBroadException
    try:
        exit_code = execute_full_run(env, logger)
    except Exception as _:
        logger.print(traceback.format_exc())
        exit_code = 1

    logger.close_logfile()
    return exit_code


def execute_full_run(env, logger):
    runner = make_full_run_service(env, logger, config_file_path(env))

    exit_code = runner.full_run()

    if runner.needs_reboot():
        logger.print()
        logger.print("Rebooting in 10 seconds...")
        sys.stdout.flush()
        time.sleep(2)
        logger.close_logfile()
        sys.stdout.flush()
        time.sleep(4)
        subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
        time.sleep(4)
        subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
        time.sleep(30)
        subprocess.run(['reboot', 'now'], shell=False, stderr=subprocess.STDOUT)

    return exit_code
