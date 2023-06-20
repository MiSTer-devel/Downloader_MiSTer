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

import sys
import urllib
from urllib.parse import urlparse

if 'unittest' in sys.modules.keys():
    import inspect
from pathlib import Path
from downloader.constants import FILE_MiSTer


def empty_store_without_base_path():
    return {
        'zips': {},
        'folders': {},
        'files': {},
        'offline_databases_imported': []
    }


def calculate_url(base_files_url, path):
    if base_files_url is None:
        raise NoArgumentsToComputeUrlError('Could not calculate URL for "%s" because "base_files_url" is not defined.' % path)

    url = base_files_url + urllib.parse.quote(path)
    return url


class NoArgumentsToComputeUrlError(Exception):
    pass


class UnreachableException(Exception):
    pass


def format_files_message(file_list):
    any_mra_files = [file for file in file_list if file[-4:].lower() == '.mra']

    rbfs = [file for file in file_list if file[-4:].lower() == '.rbf' or file == FILE_MiSTer]
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


def format_folders_message(folder_list):
    printable = [f'Folder {folder}' for folder in set(folder_list[0:10])]
    message = ', '.join(printable)
    return f'{message} + other folders.' if len(folder_list) > len(printable) else message


_calling_test_only = False


def test_only(func):
    def wrapper(*args, **kwargs):
        if 'unittest' not in sys.modules.keys():
            raise Exception('Function "%s" can only be used during "unittest" runs.' % func.__name__)

        stack = inspect.stack()
        frame = stack[1]
        global _calling_test_only
        if not _calling_test_only and 'test' not in list(Path(frame.filename).parts):
            raise Exception('Function "%s" can only be called directly from a test file.' % func.__name__)

        _calling_test_only = True
        result = func(*args, **kwargs)
        _calling_test_only = False
        return result

    return wrapper


def cache(func):
    arguments = func.__code__.co_argcount

    if arguments == 0:
        return _cached_function(func)
    elif arguments == 1:
        return _cached_method(func)

    raise Exception('Could not cache this: %s' % func.__name__)


def _cached_function(func):
    func_cached_value = None

    def wrapper():
        nonlocal func_cached_value
        if func_cached_value is None:
            func_cached_value = func()

        return func_cached_value

    return wrapper


def _cached_method(func):
    attr_name = '%s_cached_value' % func.__name__

    def wrapper(*args):
        self = args[0]
        if not isinstance(self, object):
            raise Exception('cache decorator should only be used with functions and methods with empty arguments')

        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(*args))

        return getattr(self, attr_name)

    return wrapper


class ClosableValue:
    def __init__(self, value, callback):
        self.value = value
        self._callback = callback

    def close(self):
        self._callback()
