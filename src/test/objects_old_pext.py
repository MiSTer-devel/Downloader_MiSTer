# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from typing import Dict, Any, Final

from downloader.config import default_config, Environment
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL, KENV_LOGLEVEL, FILE_MiSTer_new, K_BASE_PATH, \
    K_DOWNLOADER_RETRIES, K_FILTER, K_DATABASES, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEFAULT_BASE_PATH, \
    KENV_ALLOW_REBOOT, KENV_DEBUG, MEDIA_FAT, K_BASE_SYSTEM_PATH, K_CONFIG_PATH, K_ZIP_FILE_COUNT_THRESHOLD, K_STORAGE_PRIORITY, MEDIA_USB0, \
    MEDIA_USB1, MEDIA_USB2, KENV_FAIL_ON_FILE_ERROR, KENV_UPDATE_LINUX, KENV_CURL_SSL, KENV_COMMIT, DEFAULT_CURL_SSL_OPTIONS, \
    K_DEFAULT_DB_ID, MEDIA_USB3, KENV_LOGFILE, KENV_PC_LAUNCHER, DEFAULT_UPDATE_LINUX_ENV, K_DB_URL, K_SECTION, K_OPTIONS, K_USER_DEFINED_OPTIONS, KENV_FORCED_BASE_PATH, \
    K_MINIMUM_SYSTEM_FREE_SPACE_MB, \
    K_ZIP_ACCUMULATED_MB_THRESHOLD, FILE_MiSTer_old
from downloader.db_options import DbOptions
from downloader.other import empty_store_without_base_path
from downloader.db_entity import DbEntity, fix_folders, fix_zip
import copy
import tempfile

# @TODO: Remove this file when support for the old pext syntax '|' is removed

file_test_json_zip: Final = 'test.json.zip'
file_a: Final = 'a/A'
file_b: Final = 'b/B'
file_c: Final = 'c/C'
file_d: Final = 'd/D'
file_abc: Final = 'a/b/C'
file_nes_smb1: Final = '|games/NES/smb.nes'
file_nes_contra: Final = '|games/NES/contra.nes'
file_nes_palette_a: Final = '|games/NES/Palette/a.pal'
file_nes_manual: Final = '|docs/NES/nes.md'
file_md_sonic: Final = '|games/MegaDrive/sonic.md'
file_boot_rom: Final = 'boot.rom'
file_menu_rbf: Final = 'menu.rbf'
file_s32x_md: Final = '|docs/S32X/S32X.md'
file_neogeo_md: Final = '|docs/NeoGeo/NeoGeo.md'
file_foo: Final = 'foo.txt'
file_save_psx_castlevania: Final = 'saves/PSX/castlevania.sav'
hash_menu_rbf: Final = 'menu.rbf'
hash_MiSTer: Final = FILE_MiSTer_new
hash_PDFViewer: Final = 'pdfviewer'
hash_MiSTer_old: Final = 'something_old'
hash_real_test_file: Final = '3de8f8b0dc94b8c2230fab9ec0ba0506'
folder_a: Final = 'a'
folder_b: Final = 'b'
folder_c: Final = 'c'
folder_d: Final = 'd'
folder_ab: Final = 'a/b'
folder_games: Final = '|games'
folder_games_nes: Final = '|games/NES'
folder_games_nes_palettes: Final = '|games/NES/Palette'
folder_games_md: Final = '|games/MegaDrive'
folder_docs: Final = '|docs'
folder_docs_nes: Final = '|docs/NES'
folder_docs_neogeo: Final = '|docs/NeoGeo'
folder_docs_s32x: Final = '|docs/S32X'
folder_save_psx: Final = 'saves/PSX'
db_test: Final = 'test'
db_palettes: Final = 'db_palettes'
db_demo: Final = 'demo'
db_id_external_drives_1: Final = 'external_drives_1'
db_id_external_drives_2: Final = 'external_drives_2'
file_one: Final = 'one'
hash_one: Final = 'one'
file_big: Final = 'big'
hash_big: Final = 'big'
hash_updated_big: Final = 'updated_big'
file_reboot: Final = 'reboot.file'
hash_reboot: Final = 'reboot.hash'
db_empty: Final = 'empty'
big_size: Final = 100_000_000
binary_content: Final = b'This is a test file.'
file_size_a: Final = 2915040
file_size_b: Final = 1915040
file_size_c: Final = 3915440
file_size_d: Final = 4115440
file_size_sonic: Final = 2915020
file_size_smb1: Final = 2915020


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
    return config_with(base_path=base_path, databases={db_test: {}})


def config_test_with_filters(config_filter=None, ini_filter=None):
    return config_with(
        base_path=MEDIA_FAT,
        filter_value=None if config_filter is None else config_filter,
        default_db_id=db_test,
        databases={db_test: db_description(
            db_url='https://db.zip',
            section=db_test,
            options=None if ini_filter is None else DbOptions({K_FILTER: ini_filter})
        )},
        user_defined_options=[] if config_filter is None else [K_FILTER]
    )


def config_with(
        filter_value=None,
        base_path=None,
        base_system_path=None,
        storage_priority=None,
        config_path=None,
        zip_file_count_threshold=None,
        zip_accumulated_mb_threshold=None,
        downloader_retries=None,
        default_db_id=None,
        user_defined_options=None,
        minimum_free_space=None,
        databases: Dict[str, Any] = None):

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
    if zip_accumulated_mb_threshold is not None:
        config[K_ZIP_ACCUMULATED_MB_THRESHOLD] = zip_accumulated_mb_threshold
    if downloader_retries is not None:
        config[K_DOWNLOADER_RETRIES] = downloader_retries
    if default_db_id is not None:
        config[K_DEFAULT_DB_ID] = default_db_id
    if databases is not None:
        config[K_DATABASES] = databases
    if user_defined_options is not None:
        config[K_USER_DEFINED_OPTIONS] = user_defined_options
    if minimum_free_space is not None:
        config[K_MINIMUM_SYSTEM_FREE_SPACE_MB] = minimum_free_space
    return config


def config_with_filter(filter_value):
    return config_with(filter_value=filter_value)


def file_test_json_zip_descr():
    return {'hash': file_test_json_zip, 'unzipped_json': db_test_with_file_a().extract_props()}


def file_reboot_descr(custom_hash=None):
    return {'url': 'https://fake.com/bar', 'hash': custom_hash or hash_reboot, 'reboot': True, 'size': 23}


def db_test_being_empty_descr():
    return db_entity(db_id=db_test)


def db_reboot_descr(custom_hash=None):
    return db_entity(files={file_reboot: file_reboot_descr(custom_hash)})


def store_reboot_descr(custom_hash=None):
    return db_to_store(db_reboot_descr(custom_hash))


def temp_name():
    with tempfile.NamedTemporaryFile() as temp:
        return temp.name


def zip_desc(description, target_folder_path, zipped_files=None, summary=None, summary_hash=None, summary_size=None, contents_hash=None, contents_size=None, summary_internal_zip_id=None):
    json = {
        "kind": "extract_all_contents",
        "base_files_url": "https://base_files_url",
        "description": description,
        "contents_file": {
            "hash": contents_hash if contents_hash is not None else "4d2bf07e5d567196d9c666f1816e86e6",
            "size": contents_size if contents_size is not None else 7316038,
            "url": "https://contents_file"
        },
        "target_folder_path": target_folder_path,
    }
    if summary_internal_zip_id is not None:
        json['internal_summary'] = {} if summary is None else {
            'files': {
                file_path: {
                    **file_description,
                    'zip_id': summary_internal_zip_id,
                    **({} if 'zip_path' not in file_description else {'zip_path': file_description['zip_path']})
                } for file_path, file_description in summary['files'].items()
            },
            'folders': {
                folder_path: {
                    **folder_description,
                    'zip_id': summary_internal_zip_id,
                } for folder_path, folder_description in summary['folders'].items()
            },
        }
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
        if 'zipped_files' in zip_desc['contents_file']: del zip_desc['contents_file']['zipped_files']
        if 'unzipped_json' in zip_desc['summary_file']: del zip_desc['summary_file']['unzipped_json']

    return store


def empty_zip_summary():
    return {
        'files': {},
        "files_count": 0,
        'folders': {},
        "folders_count": 0,
    }


def db_test_with_default_filter_descr(db_default_option_filter=None):
    return db_entity(
        db_id=db_test,
        default_options=None if db_default_option_filter is None else {K_FILTER: db_default_option_filter}
    )


def db_test_descr(db_id=None, zips=None, folders=None, files=None, db_files=None, tag_dictionary=None):
    return db_entity(
        db_id=db_id or db_test,
        db_files=db_files if db_files is not None else [],
        files=files if files is not None else {},
        folders=folders if folders is not None else {},
        base_files_url='https://',
        zips=zips if zips is not None else {},
        default_options={},
        timestamp=0,
        tag_dictionary=tag_dictionary,
    )


def store_descr(zips=None, folders=None, files=None, folders_usb0=None, files_usb0=None, folders_usb1=None, files_usb1=None, folders_usb2=None, files_usb2=None, db_files=None, db_id=None, timestamp=None, base_path=None, filtered_zip_data=None):
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
    if filtered_zip_data is not None:
        store['filtered_zip_data'] = filtered_zip_data
    return store


def _add_external_drive_to_store(store, drive, folders=None, files=None):
    if files is None and folders is None:
        return

    external = {}
    if files is not None:
        external['files'] = remove_all_priority_paths(files)
        if folders is None:
            external['folders'] = {}

    if folders is not None:
        external['folders'] = remove_all_priority_paths(folders)
        if files is None:
            external['files'] = {}

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
    raw_db = db.extract_props()
    store = {
        K_BASE_PATH: "/media/fat" if base_path is None else base_path,
        "zips": raw_db["zips"],
        "folders": raw_db["folders"],
        "files": raw_db["files"],
    }
    return store


def db_description(db_url: str = None, section: str = None, options: DbOptions = None):
    description = {
        K_DB_URL: db_url if db_url is not None else DISTRIBUTION_MISTER_DB_URL,
        K_SECTION: section if section is not None else DISTRIBUTION_MISTER_DB_ID
    }
    if options is not None:
        description[K_OPTIONS] = options
    return description


def db_entity(db_id=None, db_files=None, files=None, folders=None, base_files_url=None, zips=None, default_options=None, timestamp=None, linux=None, header=None, section=None, tag_dictionary=None):
    db_props = {
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
        db_props['tag_dictionary'] = tag_dictionary
    if linux is not None:
        db_props['linux'] = linux
    if header is not None:
        db_props['header'] = header
    entity = DbEntity(db_props, section if section is not None else db_id if db_id is not None else db_test)

    if not entity.needs_migration():
        raise Exception("The db_entity created does not need migration. How is this in *_old_pext then?")

    return entity


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


def raw_db_empty_descr(zips=None):
    return {
        'db_id': db_empty,
        'db_files': [],
        'files': {},
        'folders': {},
        'base_files_url': '',
        'zips': zips or {},
        'default_options': {},
        'timestamp': 0
    }


def raw_db_descr(db_id, files=None, folders=None):
    return {
        'db_id': db_id,
        'db_files': [],
        'files': files or {},
        'folders': folders or {},
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


def db_options(download_filter=None):
    raw_db_options = {
        K_FILTER: 'all' if download_filter is None else download_filter
    }
    return DbOptions(raw_db_options)


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
        "hash": hash_code or hash_MiSTer,
        "backup": FILE_MiSTer_old,
        "path": "system",
        "reboot": True,
        "size": 2915040,
        "tmp": FILE_MiSTer_new,
        "url": "https://MiSTer",
    }


def file_mister_old_descr():
    return {
        "hash": hash_MiSTer_old,
        "size": 2915040,
        "url": "https://MiSTer",
        "reboot": True,
        "path": "system"
    }


def file_a_descr(size=None):
    return {
        "hash": file_a,
        "size": file_size_a if size is None else size,
        "url": "https://one.rbf"
    }


def files_a(size=None): return {file_a: file_a_descr(size=size)}
def files_b(size=None): return {file_b: file_b_descr(size=size)}
def files_c(size=None): return {file_c: file_c_descr(size=size)}
def files_smb1(size=None): return {file_nes_smb1: file_nes_smb1_descr(size=size)}
def files_sonic(size=None): return {file_md_sonic: file_md_sonic_descr(size=size)}


def file_b_descr(size=None):
    return {
        "hash": file_b,
        "size": file_size_b if size is None else size,
        "url": "https://two.rbf"
    }


def file_c_descr(size=None):
    return {
        "hash": file_c,
        "size": file_size_c if size is None else size,
        "url": "https://three.rbf"
    }


def file_d_descr(size=None):
    return {
        "hash": file_d,
        "size": file_size_d if size is None else size,
        "url": "https://four.rbf"
    }


def path_system(): return {'path': 'system'}


def file_system_abc_descr():
    return {
        "hash": file_abc,
        "size": 3915440,
        "url": "https://three.rbf",
        "path": "system"
    }


def file_nes_smb1_descr(size=None):
    return {
        "hash": file_nes_smb1[1:],
        "size": file_size_smb1 if size is None else size,
        "url": "https://smb.nes"
    }


def file_md_sonic_descr(size=None):
    return {
        "hash": file_md_sonic[1:],
        "size": file_size_sonic if size is None else size,
        "url": "https://sonic.md"
    }


def db_smb1(db_id=None, descr=None):
    return db_entity(db_id=db_id, folders=[folder_games, folder_games_nes], files={file_nes_smb1: file_nes_smb1_descr() if descr is None else descr})


def db_sonic(db_id=None, descr=None):
    return db_entity(db_id=db_id, folders=[folder_games, folder_games_md], files={file_md_sonic: file_md_sonic_descr() if descr is None else descr})


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


def file_nes_palette_a_descr(url: bool = True, zip_id: bool = False, tags: bool = False, zip_path: bool = False):
    return tweak_descr({
        "hash": file_nes_palette_a[1:],
        "size": 2905020,
        "url": "https://a.pal",
        "zip_id": zipped_nes_palettes_id,
        "zip_path": file_nes_palette_a.removeprefix(folder_games_nes + '/'),
        "tags": [
            "games",
            "nes",
            "palette"
        ]
    }, url=url, zip_id=zip_id, tags=tags, zip_path=zip_path)


def file_neogeo_md_descr():
    return {
        "hash": file_neogeo_md[1:],
        "size": 2905029,
        "url": "https://neogeo.md"
    }


def fix_old_pext_store(store, base_path=True, ignore: list[str] = None):
    if ignore is None:
        ignore = []
    if base_path:
        for file_path, file_description in store['files'].items():
            if file_path in ignore: continue
            if file_path.startswith('games') or file_path.startswith('docs'):
                file_description['path'] = 'pext'
        for folder_path, folder_description in store['folders'].items():
            if folder_path.startswith('games') or folder_path.startswith('docs'):
                folder_description['path'] = 'pext'
    if 'zips' in store:
        for zip_id, zip_desc in store['zips'].items():
            fix_zip(zip_desc)
    if 'filtered_zip_data' in store:
        for zip_id, zip_summary in store['filtered_zip_data'].items():
            fix_files(zip_summary['files'])
            fix_folders(zip_summary['folders'])
    if 'external' in store:
        for drive, external in store['external'].items():
            if drive in ignore: continue
            for file_path, file_description in external['files'].items():
                if file_path in ignore: continue
                if file_path.startswith('games') or file_path.startswith('docs'):
                    file_description['path'] = 'pext'
            for folder_path, folder_description in external['folders'].items():
                if folder_path.startswith('games') or folder_path.startswith('docs'):
                    folder_description['path'] = 'pext'
    return store

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


def tweak_descr(o, zip_id=True, tags=True, url=True, zip_path=False):
    if not url and 'url' in o:
        o.pop('url')
    if not zip_id and 'zip_id' in o:
        o.pop('zip_id')
    if not tags and 'tags' in o:
        o.pop('tags')
    if not zip_path and 'zip_path' in o:
        o.pop('zip_path')
    return o


def file_descr(hash_code=None, size=None, url=None, reboot=None, path=None, tags=None, unzipped_json=None, json=None):
    result = {
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


def store_with_folders(folders, db_id=None):
    return db_to_store(db_with_folders(db_id or db_test, folders))


def db_test_with_file_a(db_id=None, descr=None):
    return db_entity(db_id=db_id, db_files=[file_test_json_zip], files={file_a: file_a_descr() if descr is None else descr}, folders={folder_a: {}})


def db_test_with_file_b(db_id=None, descr=None):
    return db_entity(db_id=db_id, files={file_b: file_b_descr() if descr is None else descr}, folders={folder_b: {}})


def db_test_with_file_c(db_id=None, descr=None):
    return db_entity(db_id=db_id, files={file_c: file_c_descr() if descr is None else descr}, folders={folder_c: {}})


def db_test_with_file_d(db_id=None, descr=None):
    return db_entity(db_id=db_id, files={file_d: file_d_descr() if descr is None else descr}, folders={folder_d: {}})


def store_test_with_file_a_descr(descr=None): return db_to_store(db_test_with_file_a(descr=descr))
def store_test_with_file_b_descr(descr=None): return db_to_store(db_test_with_file_b(descr=descr))
def store_test_with_file_c_descr(descr=None): return db_to_store(db_test_with_file_c(descr=descr))
def store_test_with_smb1_descr(descr=None): return db_to_store(db_smb1(descr=descr))
def store_test_with_sonic_descr(descr=None): return db_to_store(db_sonic(descr=descr))
def store_test_with_file(file, description): return db_to_store(db_test_with_file(file, description))
def not_found_ini(): return _not_file('not_found.ini')


def _not_file(file):
    unittest.TestCase().assertFalse(Path(file).is_file())
    return file


def default_base_path():
    return '/media/fat'


def default_env() -> Environment:
    return {
        KENV_DEFAULT_DB_URL: DISTRIBUTION_MISTER_DB_URL,
        KENV_DEFAULT_DB_ID: DISTRIBUTION_MISTER_DB_ID,
        KENV_DEFAULT_BASE_PATH: default_base_path(),
        KENV_FORCED_BASE_PATH: None,
        KENV_ALLOW_REBOOT: None,
        KENV_DEBUG: 'false',
        KENV_CURL_SSL: DEFAULT_CURL_SSL_OPTIONS,
        KENV_UPDATE_LINUX: DEFAULT_UPDATE_LINUX_ENV,
        KENV_FAIL_ON_FILE_ERROR: 'false',
        KENV_COMMIT: 'unknown',
        KENV_LOGFILE: None,
        KENV_LOGLEVEL: '',
        KENV_PC_LAUNCHER: None,
    }


def debug_env():
    env = default_env()
    env[KENV_DEBUG] = 'true'
    return env


def path_with(path, added_part):
    return '%s/%s' % (path, added_part)


zipped_nes_palettes_id = 'zipped_nes_palettes_id'
