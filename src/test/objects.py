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
import unittest
from pathlib import Path

from downloader.config import default_config
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, FILE_MiSTer_new, K_BASE_PATH, \
    K_UPDATE_LINUX, K_DOWNLOADER_SIZE_MB_LIMIT, K_DOWNLOADER_PROCESS_LIMIT, K_DOWNLOADER_TIMEOUT, \
    K_DOWNLOADER_RETRIES, K_FILTER, K_DATABASES, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, \
    KENV_ALLOW_REBOOT, KENV_DEBUG, \
    MEDIA_FAT, K_BASE_SYSTEM_PATH, K_CONFIG_PATH, K_ZIP_FILE_COUNT_THRESHOLD, K_STORAGE_PRIORITY, MEDIA_USB0, \
    MEDIA_USB1, \
    MEDIA_USB2, KENV_FAIL_ON_FILE_ERROR, KENV_UPDATE_LINUX, KENV_CURL_SSL, KENV_COMMIT, DEFAULT_CURL_SSL_OPTIONS, \
    K_DEFAULT_DB_ID, MEDIA_USB3, KENV_LOGFILE, KENV_PC_LAUNCHER
from downloader.db_options import DbOptions, DbOptionsKind
from downloader.other import empty_store_without_base_path
from test.fake_db_entity import DbEntity
import copy
import tempfile

file_test_json_zip = 'test.json.zip'
file_a = 'a/A'
file_b = 'b/B'
file_c = 'c/C'
file_nes_smb1 = '|games/NES/smb.nes'
file_nes_contra = '|games/NES/contra.nes'
file_nes_palette_a = '|games/NES/Palette/a.pal'
file_nes_manual = '|docs/NES/nes.md'
file_boot_rom = 'boot.rom'
file_menu_rbf = 'menu.rbf'
file_s32x_md = '|docs/S32X/S32X.md'
file_neogeo_md = '|docs/NeoGeo/NeoGeo.md'
file_foo = 'foo.txt'
file_save_psx_castlevania = 'saves/PSX/castlevania.sav'
hash_menu_rbf = 'menu.rbf'
hash_MiSTer = FILE_MiSTer_new
hash_PDFViewer = 'pdfviewer'
hash_MiSTer_old = 'something_old'
hash_real_test_file = '3de8f8b0dc94b8c2230fab9ec0ba0506'
folder_a = 'a'
folder_b = 'b'
folder_c = 'c'
folder_games = '|games'
folder_games_nes = '|games/NES'
folder_games_nes_palettes = '|games/NES/Palette'
folder_docs = '|docs'
folder_docs_nes = '|docs/NES'
folder_docs_neogeo = '|docs/NeoGeo'
folder_docs_s32x = '|docs/S32X'
folder_save_psx = 'saves/PSX'
db_test = 'test'
db_palettes = 'db_palettes'
db_demo = 'demo'
db_id_external_drives_1 = 'external_drives_1'
db_id_external_drives_2 = 'external_drives_2'
file_one = 'one'
hash_one = 'one'
file_big = 'big'
hash_big = 'big'
hash_updated_big = 'updated_big'
db_empty = 'empty'
big_size = 100_000_000


def media_fat(path):
    return media_drive(MEDIA_FAT, path)


def media_usb0(path):
    return media_drive(MEDIA_USB0, path)


def media_usb1(path):
    return media_drive(MEDIA_USB1, path)


def media_usb2(path):
    return media_drive(MEDIA_USB2, path)


def media_usb3(path):
    return media_drive(MEDIA_USB3, path)


def media_drive(drive, path):
    if isinstance(path, list):
        return map(lambda p: media_drive(drive, p), path)
    return '%s/%s' % (drive, remove_priority_path(path))


def empty_config():
    return {}


def config_test(base_path=MEDIA_FAT):
    config = config_with(base_path=base_path)
    config[K_DATABASES] = {db_test: {}}
    return config


def config_with(filter_value=None, base_path=None, base_system_path=None, storage_priority=None, config_path=None, zip_file_count_threshold=None, downloader_retries=None, default_db_id=None):
    config = default_config()
    if filter_value is not None:
        config[K_FILTER] = filter_value
    if base_path is not None:
        config[K_BASE_PATH] = base_path.lower()
    if base_system_path is not None:
        config[K_BASE_SYSTEM_PATH] = base_system_path.lower()
    if storage_priority is not None:
        config[K_STORAGE_PRIORITY] = storage_priority.lower()
    if config_path is not None:
        config[K_CONFIG_PATH] = Path(config_path)
    if zip_file_count_threshold is not None:
        config[K_ZIP_FILE_COUNT_THRESHOLD] = zip_file_count_threshold
    if downloader_retries is not None:
        config[K_DOWNLOADER_RETRIES] = downloader_retries
    if default_db_id is not None:
        config[K_DEFAULT_DB_ID] = default_db_id
    return config


def config_with_filter(filter_value):
    return config_with(filter_value=filter_value)


def file_test_json_zip_descr():
    return {'hash': file_test_json_zip, 'unzipped_json': db_test_with_file_a().testable}


def db_test_being_empty_descr():
    return db_entity(db_id=db_test)


def temp_name():
    with tempfile.NamedTemporaryFile() as temp:
        return temp.name


def zip_desc(description, target_folder_path, zipped_files=None, summary=None, summary_hash=None, summary_size=None, contents_hash=None, contents_size=None, is_summary_internal=False):
    json = {
        "kind": "extract_all_contents",
        "base_files_url": "https://base_files_url",
        "description": description,
        "contents_file": {
            "hash": contents_hash if contents_hash is not None else "4d2bf07e5d567196d9c666f1816e86e6",
            "size": contents_size if contents_size is not None else 7316038,
            "url": "https://contents_file"
        },
        "files_count": 1858,
        "folders_count": 0,
        "target_folder_path": target_folder_path,
        "raw_files_size": 6995290
    }
    if is_summary_internal:
        json['internal_summary'] = {} if summary is None else summary
    else:
        json['summary_file'] = {
            "hash": summary_hash if summary_hash is not None else "b5d85d1cd6f92d714ab74a997b97130d",
            "size": summary_size if summary_size is not None else 84460,
            "url": "https://summary_file"
        }
        if summary is not None:
            json['summary_file']['unzipped_json'] = summary

    if zipped_files is not None:
        json['contents_file']['zipped_files'] = zipped_files

    return json


def clean_zip_test_fields(store):
    for zip_desc in store['zips'].values():
        del zip_desc['contents_file']['zipped_files']
        del zip_desc['summary_file']['unzipped_json']

    return store


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


def store_descr(zips=None, folders=None, files=None, folders_usb0=None, files_usb0=None, folders_usb1=None, files_usb1=None, folders_usb2=None, files_usb2=None, db_files=None, db_id=None, timestamp=None, base_path=None):
    store = db_to_store(db_entity(
        db_id=db_id,
        db_files=db_files,
        files=remove_all_priority_paths(files),
        folders=remove_all_priority_paths(folders),
        zips=zips,
        timestamp=timestamp
    ), base_path=base_path)
    _add_external_drive_to_store(store, '/media/usb0', folders_usb0, files_usb0)
    _add_external_drive_to_store(store, '/media/usb1', folders_usb1, files_usb1)
    _add_external_drive_to_store(store, '/media/usb2', folders_usb2, files_usb2)
    return store


def _add_external_drive_to_store(store, drive, folders=None, files=None):
    if files is None and folders is None:
        return

    external = {}
    if files is not None:
        external['files'] = remove_all_priority_paths(files)

    if folders is not None:
        external['folders'] = remove_all_priority_paths(folders)

    if 'external' not in store:
        store['external'] = {}

    store['external'][drive] = external


def remove_all_priority_paths(container):
    if isinstance(container, dict):
        container = {remove_priority_path(k): v for k, v in container.items()}
    elif isinstance(container, list):
        container = [remove_priority_path(k) for k in container]
    return container


def remove_priority_path(path):
    if path[0] == '|':
        return path[1:]
    else:
        return path


def db_to_store(db, base_path=None):
    raw_db = db.testable
    return {
        K_BASE_PATH: "/media/fat" if base_path is None else base_path,
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
        'folders': _fix_folders(folders) if folders is not None else {},
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


def _fix_folders(folders):
    if isinstance(folders, list):
        folders = {f: {} for f in folders}
    return folders


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


def db_options(kind=None, base_path=None, update_linux=None, downloader_size_mb_limit=None, downloader_process_limit=None, downloader_timeout=None, downloader_retries=None, download_filter=None):
    raw_db_options = {
        K_UPDATE_LINUX: False if update_linux is None else update_linux,
        K_DOWNLOADER_SIZE_MB_LIMIT: 5 if downloader_size_mb_limit is None else downloader_size_mb_limit,
        K_DOWNLOADER_PROCESS_LIMIT: 3 if downloader_process_limit is None else downloader_process_limit,
        K_DOWNLOADER_TIMEOUT: 1 if downloader_timeout is None else downloader_timeout,
        K_DOWNLOADER_RETRIES: 100 if downloader_retries is None else downloader_retries,
        K_FILTER: 'all' if download_filter is None else download_filter
    }
    kind = DbOptionsKind.INI_SECTION if kind is None else kind
    if base_path is not None:
        raw_db_options[K_BASE_PATH] = base_path
    elif kind == DbOptionsKind.INI_SECTION:
        raw_db_options[K_BASE_PATH] = '/media/usb0'
    return DbOptions(raw_db_options, kind)


def file_pdfviewer_descr():
    return {
        "hash": hash_PDFViewer,
        "size": 2915040,
        "url": "https://pdfviewer",
        "path": "system"
    }


def with_base_path(description, base_path):
    description['base_path'] = base_path
    return description


def file_mister_descr(hash_code=None):
    return {
        "delete": [],
        "hash": hash_code or hash_MiSTer,
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


def file_b_descr(delete=None):
    return {
        "delete": delete if delete is not None else [],
        "hash": file_b,
        "size": 1915040,
        "url": "https://two.rbf"
    }


def file_nes_smb1_descr():
    return {
        "hash": file_nes_smb1[1:],
        "size": 2915020,
        "url": "https://smb.nes"
    }


def file_nes_manual_descr():
    return {
        "hash": file_nes_manual[1:],
        "size": 22125020,
        "url": "https://nes.md"
    }


def file_nes_contra_descr():
    return {
        "hash": file_nes_contra[1:],
        "size": 2915010,
        "url": "https://contra.nes"
    }


def file_nes_palette_a_descr():
    return {
        "hash": file_nes_palette_a[1:],
        "size": 2905020,
        "url": "https://a.pal"
    }


def file_neogeo_md_descr():
    return {
        "hash": file_neogeo_md[1:],
        "size": 2905029,
        "url": "https://neogeo.md"
    }


def file_s32x_md_descr():
    return {
        "hash": file_s32x_md[1:],
        "size": 2905019,
        "url": "https://s32x.md"
    }


def file_foo_descr():
    return {
        "hash": file_foo,
        "size": 2305019,
        "url": "https://file.foo"
    }


def file_save_psx_castlevania_descr(overwrite=None):
    o = {
        "hash": file_save_psx_castlevania,
        "size": 23053019,
        "url": "https://psx_castlevania.sav"
    }
    if overwrite is not None:
        o['overwrite'] = overwrite
    return o


def tweak_descr(o, zip_id=True, tags=True, url=True):
    if not url:
        o.pop('url')
    if not zip_id:
        o.pop('zip_id')
    if not tags:
        o.pop('tags')
    return o


def file_descr(delete=None, hash_code=None, size=None, url=None, reboot=None, path=None, tags=None, unzipped_json=None, json=None):
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
    if unzipped_json is not None:
        result["unzipped_json"] = unzipped_json
    if json is not None:
        result["json"] = json
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


def with_overwrite(descr, overwrite):
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


def db_distribution_mister(files=None, folders=None):
    return db_entity(db_id=DISTRIBUTION_MISTER_DB_ID, db_files=[file_test_json_zip], files=files, folders=folders)


def db_with_file(db_id, name_file, file):
    return db_entity(db_id=db_id, db_files=[db_id + '.json.zip'], files={name_file: file})


def db_with_folders(db_id, folders):
    if isinstance(folders, list):
        folders = {f: {} for f in folders}
    return db_entity(db_id=db_id, db_files=[db_id + '.json.zip'], folders=folders)


def db_with_files(db_id, files):
    return db_entity(db_id=db_id, db_files=[db_id + '.json.zip'], files=files)


def empty_store(base_path):
    return {K_BASE_PATH: base_path, **empty_store_without_base_path()}


def empty_test_store():
    return empty_store(base_path=MEDIA_FAT)


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


default_base_path = '/tmp/default_base_path'


def default_env():
    return {
        KENV_DEFAULT_DB_URL: DISTRIBUTION_MISTER_DB_URL,
        KENV_DEFAULT_DB_ID: DISTRIBUTION_MISTER_DB_ID,
        KENV_DEFAULT_BASE_PATH: default_base_path,
        KENV_ALLOW_REBOOT: None,
        KENV_DEBUG: 'false',
        KENV_CURL_SSL: DEFAULT_CURL_SSL_OPTIONS,
        KENV_UPDATE_LINUX: 'true',
        KENV_FAIL_ON_FILE_ERROR: 'false',
        KENV_COMMIT: 'unknown',
        KENV_LOGFILE: None,
        KENV_PC_LAUNCHER: None,
    }


def debug_env():
    env = default_env()
    env[KENV_DEBUG] = 'true'
    return env


def path_with(path, added_part):
    return '%s/%s' % (path, added_part)
