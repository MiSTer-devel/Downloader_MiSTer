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

from downloader.config import default_config
from downloader.constants import distribution_mister_db_id, distribution_mister_db_url, file_MiSTer_new
from downloader.db_options import DbOptions, DbOptionsKind
from test.fake_db_entity import DbEntity
import copy
import tempfile

file_test_json_zip = 'test.json.zip'
file_a = 'a/A'
file_b = 'b/B'
file_c = 'c/C'
file_boot_rom = 'boot.rom'
file_menu_rbf = 'menu.rbf'
hash_menu_rbf = 'menu.rbf'
hash_MiSTer = file_MiSTer_new
hash_MiSTer_old = 'something_old'
hash_real_test_file = '3de8f8b0dc94b8c2230fab9ec0ba0506'
folder_a = 'a'
folder_b = 'b'
folder_c = 'c'
db_test = 'test'
file_one = 'one'
hash_one = 'one'
file_big = 'big'
hash_big = 'big'
hash_updated_big = 'updated_big'
db_empty = 'empty'

def config_with_filter(filter_value):
    config = default_config()
    config['filter'] = filter_value
    return config

def file_test_json_zip_descr():
    return {'hash': file_test_json_zip, 'unzipped_json': db_test_with_file_a().testable}


def db_test_being_empty_descr():
    return db_entity(db_id=db_test)


def temp_name():
    with tempfile.NamedTemporaryFile() as temp:
        return temp.name


def zip_desc(contents, path, source, zipped_files=None, unzipped_json=None, summary_hash=None, summary_size=None, contents_hash=None, contents_size=None):
    json = {
        "base_files_url": "https://base_files_url",
        "contents": contents,
        "contents_file": {
            "hash": contents_hash if contents_hash is not None else "4d2bf07e5d567196d9c666f1816e86e6",
            "size": contents_size if contents_size is not None else 7316038,
            "url": "https://contents_file"
        },
        "files_count": 1858,
        "folders_count": 0,
        "path": path,
        "raw_files_size": 6995290,
        "source": source,
        "summary_file": {
            "hash": summary_hash if summary_hash is not None else "b5d85d1cd6f92d714ab74a997b97130d",
            "size": summary_size if summary_size is not None else 84460,
            "url": "https://summary_file"
        }
    }
    if zipped_files is not None:
        json['contents_file']['zipped_files'] = zipped_files
    if unzipped_json is not None:
        json['summary_file']['unzipped_json'] = unzipped_json
    return json


def empty_zip_summary():
    return {
        'files': {},
        "files_count": 0,
        'folders': {},
        "folders_count": 0,
    }

def db_test_descr(zips=None, folders=None, files=None, db_files=None, tag_dictionary=None):
    return db_entity(
        db_id=db_test,
        db_files=db_files if db_files is not None else [],
        files=files if files is not None else {},
        folders=folders if folders is not None else {},
        base_files_url='https://',
        zips=zips if zips is not None else {},
        default_options={},
        timestamp=0,
        tag_dictionary=tag_dictionary
    )


def store_test_descr(zips=None, folders=None, files=None, db_files=None):
    return db_to_store(db_entity(
        db_id=db_test,
        db_files=db_files if db_files is not None else [],
        files=files if files is not None else {},
        folders=folders if folders is not None else {},
        base_files_url='https://',
        zips=zips if zips is not None else {},
        default_options={},
        timestamp=0
    ))


def db_to_store(db):
    raw_db = db.testable
    return {
        "zips": raw_db["zips"],
        "folders": raw_db["folders"],
        "files": raw_db["files"],
        "offline_databases_imported": []
    }


def db_entity(db_id=None, db_files=None, files=None, folders=None, base_files_url=None, zips=None, default_options=None, timestamp=None, linux=None, header=None, section=None, tag_dictionary=None):
    db_raw = {
        'db_id': db_id if db_id is not None else db_test,
        'db_files': db_files if db_files is not None else [],
        'files': files if files is not None else {},
        'folders': folders if folders is not None else {},
        'base_files_url': base_files_url if base_files_url is not None else '',
        'zips': zips if zips is not None else {},
        'default_options': default_options if default_options is not None else {},
        'timestamp': timestamp if timestamp is not None else 0
    }
    if tag_dictionary is not None:
        db_raw['tag_dictionary'] = tag_dictionary
    if linux is not None:
        db_raw['linux'] = linux
    if header is not None:
        db_raw['header'] = header
    return DbEntity(db_raw, section if section is not None else db_id if db_id is not None else db_test)


def raw_db_empty_with_linux_descr():
    return {
        'db_id': db_empty,
        'db_files': [],
        'files': {},
        'folders': {},
        'linux': {
            "delete": [],
            "hash": "d3b619c54c4727ab618bf108013f79d9",
            "size": 83873790,
            "url": "https://raw.githubusercontent.com/MiSTer-devel/SD-Installer-Win64_MiSTer/136d7d8ea24b1de2424574b2d31f527d6b3e3d39/release_20210711.rar",
            "version": "210711"
        },
        'base_files_url': '',
        'zips': {},
        'default_options': {},
        'timestamp': 0
    }


def raw_db_empty_descr():
    return {
        'db_id': db_empty,
        'db_files': [],
        'files': {},
        'folders': {},
        'base_files_url': '',
        'zips': {},
        'default_options': {},
        'timestamp': 0
    }


def raw_db_wrong_descr():
    return {
        'db_id': 'wrong',
        'db_files': [],
        'files': {},
        'folders': {},
        'base_files_url': '',
        'zips': {},
        'default_options': {},
        'timestamp': 0
    }


def db_options(kind=None, base_path=None, parallel_update=None, update_linux=None, downloader_size_mb_limit=None, downloader_process_limit=None, downloader_timeout=None, downloader_retries=None):
    raw_db_options = {
        'parallel_update': False if parallel_update is None else parallel_update,
        'update_linux': False if update_linux is None else update_linux,
        'downloader_size_mb_limit': 5 if downloader_size_mb_limit is None else downloader_size_mb_limit,
        'downloader_process_limit': 3 if downloader_process_limit is None else downloader_process_limit,
        'downloader_timeout': 1 if downloader_timeout is None else downloader_timeout,
        'downloader_retries': 100 if downloader_retries is None else downloader_retries,
    }
    kind = DbOptionsKind.INI_SECTION if kind is None else kind
    if base_path is not None:
        raw_db_options['base_path'] = base_path
    elif kind == DbOptionsKind.INI_SECTION:
        raw_db_options['base_path'] = '/media/usb0/'
    return DbOptions(raw_db_options, kind)


def file_mister_descr():
    return {
        "delete": [],
        "hash": hash_MiSTer,
        "size": 2915040,
        "url": "https://MiSTer",
        "reboot": True,
        "path": "system"
    }


def file_mister_old_descr():
    return {
        "delete": [],
        "hash": hash_MiSTer_old,
        "size": 2915040,
        "url": "https://MiSTer",
        "reboot": True,
        "path": "system"
    }


def file_a_descr(delete=None):
    return {
        "delete": delete if delete is not None else [],
        "hash": file_a,
        "size": 2915040,
        "url": "https://one.rbf"
    }


def file_descr(delete=None, hash_code=None, size=None, url=None, reboot=None, path=None, tags=None):
    result = {
        "delete": delete if delete is not None else [],
        "hash": hash_code if hash_code is not None else file_a,
        "size": size if size is not None else 2915040,
        "url": url if url is not None else "https://one.rbf",
        "reboot": reboot if reboot is not None else False,
        "path": path if path is not None else "common",
    }
    if tags is not None:
        result["tags"] = tags
    return result


def zipped_file_a_descr(zip_id, url=False):
    o = {
        "hash": file_a,
        "size": 2915040,
        "zip_id": zip_id
    }
    if url:
        o["url"] = 'https://' + file_a
    return o


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
    return db_entity(db_id=db_test, db_files=[file_test_json_zip], files={name_file: file})


def db_distribution_mister_with_file(name_file, file):
    return db_entity(db_id=distribution_mister_db_id, db_files=[file_test_json_zip], files={name_file: file})


def db_with_file(db_id, name_file, file):
    return db_entity(db_id=db_id, db_files=[db_id + '.json.zip'], files={name_file: file})


def db_with_folders(db_id, folders):
    if isinstance(folders, list):
        folders = {f: {} for f in folders}
    return db_entity(db_id=db_id, db_files=[db_id + '.json.zip'], folders=folders)


def store_with_folders(db_id, folders):
    return db_to_store(db_with_folders(db_id, folders))


def db_test_with_file_a(input_descr=None):
    descr = file_a_descr() if input_descr is None else input_descr
    return db_entity(db_id=db_test, db_files=[file_test_json_zip], files={file_a: descr}, folders={folder_a: {}})


def store_test_with_file_a_descr():
    return db_to_store(db_test_with_file_a())


def store_test_with_file(file, description):
    return db_to_store(db_test_with_file(file, description))


def not_found_ini():
    return _not_file('not_found.ini')


def _not_file(file):
    unittest.TestCase().assertFalse(Path(file).is_file())
    return file


default_base_path = '/tmp/default_base_path/'


def default_env():
    return {
        'DEFAULT_DB_URL': distribution_mister_db_url,
        'DEFAULT_DB_ID': distribution_mister_db_id,
        'DEFAULT_BASE_PATH': default_base_path,
        'ALLOW_REBOOT': None,
        'DEBUG': 'false'
    }


def debug_env():
    env = default_env()
    env['DEBUG'] = 'true'
    return env
