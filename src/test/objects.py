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

import unittest
from pathlib import Path
import copy

file_test_json_zip = 'test.json.zip'
file_a = 'A'
file_boot_rom = 'boot.rom'
file_menu_rbf = 'menu.rbf'
hash_menu_rbf = 'menu.rbf'
file_MiSTer = 'MiSTer'
hash_MiSTer = 'MiSTer.new'
file_MiSTer_new = 'MiSTer.new'
folder_a = 'a'
db_test = 'test'
file_one = 'one'
hash_one = 'one'


def file_test_json_zip_descr():
    return {'hash': file_test_json_zip, 'unzipped_json': db_test_with_file_a_descr()}


def db_empty_descr():
    return {
        'db_id': db_test,
        'db_files': [''],
        'files': {},
        'folders': []
    }


def file_mister_descr():
    return {
        "delete": [],
        "hash": hash_MiSTer,
        "size": 2915040,
        "url": "https://MiSTer",
        "reboot": True,
        "path": "system"
    }


def file_a_descr():
    return {
        "delete": [],
        "hash": file_a,
        "size": 2915040,
        "url": "https://one.rbf"
    }


def boot_rom_descr():
    return {
        "delete": [],
        "hash": file_boot_rom,
        "size": 29315040,
        "url": "https://boot.rom",
        "overwrite": False
    }


def overwrite_file(descr, overwrite):
    result = copy.deepcopy(descr)
    result['overwrite'] = overwrite
    return result


def file_a_updated_descr():
    return {
        "delete": [],
        "hash": "B946e696994573394343edb74c54180c",
        "size": 2915040,
        "url": "https://one.rbf"
    }


def db_test_with_file(name_file, file):
    return {
        'db_id': db_test,
        'db_files': [file_test_json_zip],
        'files': {
            name_file: file
        },
        'folders': []
    }


def db_with_file(db_id, name_file, file):
    return {
        'db_id': db_id,
        'db_files': [db_id + '.json.zip'],
        'files': {
            name_file: file
        },
        'folders': []
    }


def db_test_with_file_a_descr():
    return {
        'db_id': db_test,
        'db_files': [file_test_json_zip],
        'files': {
            file_a: file_a_descr()
        },
        'folders': [folder_a]
    }


def not_found_sh():
    return _not_file('not_found.sh')


def not_found_ini():
    return _not_file('not_found.ini')


def _not_file(file):
    unittest.TestCase().assertFalse(Path(file).is_file())
    return file


def default_env():
    return {
        'DEFAULT_DB_URL': 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
        'DEFAULT_DB_ID': 'distribution_mister',
        'ALLOW_REBOOT': None
    }
