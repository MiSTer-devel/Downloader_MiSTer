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

import subprocess
from pathlib import Path


def empty_store():
    return {
        'zips': {},
        'folders': {},
        'files': {},
        'offline_databases_imported': []
    }


def format_files_message(file_list):
    any_mra_files = [file for file in file_list if file[-4:].lower() == '.mra']

    rbfs = [file for file in file_list if file[-4:].lower() == '.rbf' or file == 'MiSTer']
    mras = [file for file in any_mra_files if '/_alternatives/' not in file.lower()]
    alts = [file for file in any_mra_files if '/_alternatives/' in file.lower()]
    urls = [file for file in file_list if file[0:4].lower() == 'http']

    printable = None
    if len(rbfs) + len(mras) > 100 and len(mras) > 0:
        printable = [Path(file).name for file in rbfs] + urls
        printable.append('MRAs')
    else:
        printable = [Path(file).name for file in (rbfs + mras)] + urls

    if len(alts) > 0:
        printable.append('MRA Alternatives')

    there_are_other_files = False
    if len(printable) == 0:
        printable = [Path(file).name for file in file_list[0:25]]
        there_are_other_files = len(file_list) > len(printable)
    else:
        there_are_other_files = len(file_list) > (len(rbfs) + len(mras) + len(alts) + len(urls))

    message = ', '.join(printable)
    if there_are_other_files:
        message = '%s + other files.' % message

    return 'none.' if message == '' else message


def run_successfully(command, logger):
    result = subprocess.run(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    stdout = result.stdout.decode()
    stderr = result.stderr.decode()
    if stdout.strip():
        logger.print(stdout)

    if stderr.strip():
        logger.print(stderr)

    if result.returncode != 0:
        raise Exception("subprocess.run %s Return Code was '%d'" % (command, result.returncode))


def run_stdout(command):
    result = subprocess.run(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    if result.returncode != 0:
        raise Exception("subprocess.run %s Return Code was '%d'" % (command, result.returncode)
                        + '\n' + result.stdout.decode() + '\n' + result.stderr.decode())

    return result.stdout.decode()
