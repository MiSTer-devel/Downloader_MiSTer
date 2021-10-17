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
file_MiSTer_old = 'Scripts/.config/downloader/MiSTer.old'
hash_MiSTer = 'MiSTer.new'
file_MiSTer_new = 'MiSTer.new'
folder_a = 'a'
db_test = 'test'
file_one = 'one'
hash_one = 'one'
db_empty = 'empty'
cheats_folder_nes_zip_id = 'cheats_folder_nes'
cheats_folder_nes_folders = {'Cheats/NES': {}}
cheats_folder_nes_file_path = 'Cheats/NES/10-Yard Fight (USA, Europe) [3D564757].zip'
cheats_folder_nes_file_url = "http://Cheats/NES/10-Yard Fight (USA, Europe) [3D564757].zip"
cheats_folder_nes_file_hash = "8c02595feff096a9dd160e559067f4f4"
cheats_folder_nes_file_size = 1020


def file_test_json_zip_descr():
    return {'hash': file_test_json_zip, 'unzipped_json': db_test_with_file_a_descr()}


def db_test_being_empty_descr():
    return {
        'db_id': db_test,
        'db_files': [''],
        'files': {},
        'folders': {},
        'base_files_url': '',
        'zips': {}
    }


def cheats_folder_nes_zip_desc(zipped_files=None, unzipped_json=None, folders=None):
    json = {
        "base_files_url": "https://base_files_url",
        "contents": [
            "NES"
        ],
        "contents_file": {
            "hash": "4d2bf07e5d567196d9c666f1816e86e6",
            "size": 7316038,
            "url": "https://contents_file"
        },
        "files_count": 1858,
        "folders_count": 0,
        "path": "Cheats/",
        "raw_files_size": 6995290,
        "source": "Cheats/NES",
        "summary_file": {
            "hash": "b5d85d1cd6f92d714ab74a997b97130d",
            "size": 84460,
            "url": "https://summary_file"
        }
    }
    if zipped_files is not None:
        json['contents_file']['zipped_files'] = zipped_files
    if unzipped_json is not None:
        json['summary_file']['unzipped_json'] = unzipped_json
    if folders is not None:
        json['folders'] = folders
    return json


def unzipped_json_with_cheats_folder_nes_file():
    return {
        'files': {
            cheats_folder_nes_file_path: {
                "hash": cheats_folder_nes_file_hash,
                "size": cheats_folder_nes_file_size,
                "zip_id": cheats_folder_nes_zip_id
            },
        },
        "files_count": 1,
        'folders': cheats_folder_nes_folders,
        "folders_count": 1,
    }


def store_with_unzipped_cheats_folder_nes_files(url=True, folders=True, zip_id=True, zips=True, zip_folders=True, online_database_imported=None):
    o = {
        "files": {
            cheats_folder_nes_file_path: {
                'hash': cheats_folder_nes_file_hash,
                'size': cheats_folder_nes_file_size,
                'url': cheats_folder_nes_file_url,
                'zip_id': cheats_folder_nes_zip_id
            }
        },
        'folders': cheats_folder_nes_folders,
        'offline_databases_imported': online_database_imported if online_database_imported is not None else [],
        "zips": {
            cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(folders=cheats_folder_nes_folders)
        }
    }
    if not folders:
        o.pop('folders')
    if not url:
        o['files'][cheats_folder_nes_file_path].pop('url')
    if not zip_id:
        o['files'][cheats_folder_nes_file_path].pop('zip_id')
    if not zips:
        o['zips'] = {}
    if not zip_folders:
        o['zips'][cheats_folder_nes_zip_id].pop('folders')
    return o


def db_test_descr(zips=None, folders=None, files=None, db_files=None):
    return {
        'db_id': db_test,
        'db_files': db_files if db_files is not None else [''],
        'files': files if files is not None else {},
        'folders': folders if folders is not None else {},
        'base_files_url': 'http://',
        'zips': zips if zips is not None else {}
    }


def db_empty_with_linux_descr():
    return {
        'db_id': db_empty,
        'db_files': [],
        'files': [],
        'folders': {},
        'linux': {
            "delete": [],
            "hash": "d3b619c54c4727ab618bf108013f79d9",
            "size": 83873790,
            "url": "https://raw.githubusercontent.com/MiSTer-devel/SD-Installer-Win64_MiSTer/136d7d8ea24b1de2424574b2d31f527d6b3e3d39/release_20210711.rar",
            "version": "210711"
        },
        'base_files_url': '',
        'zips': {}
    }


def db_empty_descr():
    return {
        'db_id': db_empty,
        'db_files': [],
        'files': [],
        'folders': {},
        'base_files_url': '',
        'zips': {}
    }


def db_wrong_descr():
    return {
        'db_id': 'wrong',
        'db_files': [],
        'files': [],
        'folders': {},
        'base_files_url': '',
        'zips': {}
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
        'folders': {},
        'base_files_url': '',
        'zips': {}
    }


def db_with_file(db_id, name_file, file):
    return {
        'db_id': db_id,
        'db_files': [db_id + '.json.zip'],
        'files': {
            name_file: file
        },
        'folders': {},
        'base_files_url': '',
        'zips': {}
    }


def db_with_folders(db_id, folders):
    return {
        'db_id': db_id,
        'db_files': [db_id + '.json.zip'],
        'files': {},
        'folders': folders,
        'base_files_url': '',
        'zips': {}
    }


def db_test_with_file_a_descr():
    return {
        'db_id': db_test,
        'db_files': [file_test_json_zip],
        'files': {
            file_a: file_a_descr()
        },
        'folders': {folder_a: {}},
        'base_files_url': '',
        'zips': {}
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
