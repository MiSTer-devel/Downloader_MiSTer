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
import json
import unittest

from downloader.constants import MEDIA_FAT, MEDIA_USB0, FILE_downloader_storage, FILE_downloader_external_storage
from downloader.local_store_wrapper import LocalStoreWrapper
from downloader.store_migrator import make_new_local_store
from test.fake_store_migrator import StoreMigrator
from test.objects import media_fat, db_test, file_descr, file_b, file_b_descr, media_usb0, \
    store_descr, file_a, file_a_descr, folder_a, folder_b, db_demo, file_nes_smb1, file_nes_smb1_descr, folder_games, \
    folder_games_nes, file_nes_manual, file_nes_manual_descr, folder_docs, folder_docs_nes
from test.fake_file_system_factory import FileSystemFactory
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_local_repository import LocalRepository


internal_db_fat_zip_file = media_fat(FILE_downloader_storage).lower()
usb0_db_json_file = media_usb0(FILE_downloader_external_storage).lower()


def db_files_usb0_b(): return {usb0_db_json_file: store_to_db_files(store_usb0_b_internal_a())[MEDIA_USB0]}
def db_files_usb0_b_games(): return {usb0_db_json_file: store_to_db_files(store_usb0_b_games_internal_a_docs())[MEDIA_USB0]}
def db_files_internal_a_usb0_b(): return {**db_files_internal_a(), **db_files_usb0_b()}
def db_files_internal_a_docs_usb0_b_games(): return {**db_files_internal_a_docs(), **db_files_usb0_b_games()}
def db_files_internal_empty(): return {internal_db_fat_zip_file: {}}
def db_files_internal_a(): return {internal_db_fat_zip_file: store_internal_a()}
def db_files_internal_a_docs(): return {internal_db_fat_zip_file: store_to_db_files(store_usb0_b_games_internal_a_docs())[MEDIA_FAT]}
def files_a(): return {file_a: file_a_descr()}
def folders_a(): return {folder_a: {}}
def files_b(): return {file_b: file_b_descr()}
def folders_b(): return {folder_b: {}}
def files_games(): return {file_nes_smb1: file_nes_smb1_descr()}
def folders_games(): return {folder_games: {}, folder_games_nes: {}}
def files_docs(): return {file_nes_manual: file_nes_manual_descr()}
def folders_docs(): return {folder_docs: {}, folder_docs_nes: {}}
def store_internal_a(): return {db_test: store_descr(files=files_a(), folders=folders_a())}
def store_internal_a_docs(): return {db_test: store_descr(files={**files_a(), **files_docs()}, folders={**folders_a(), **folders_docs()})}
def store_usb0_b_internal_a(): return {db_test: store_descr(files=files_a(), folders=folders_a(), folders_usb0=folders_b(), files_usb0=files_b())}
def store_usb0_games_internal_docs(): return {db_demo: store_descr(files=files_docs(), folders=folders_docs(), folders_usb0=folders_games(), files_usb0=files_games())}
def store_usb0_b_games_internal_a_docs(): return {**store_usb0_b_internal_a(), **store_usb0_games_internal_docs()}


class TestLocalRepository(unittest.TestCase):

    def test_save_store___on_empty_fs_with_input_store_empty___stores_internal_empty(self):
        actual = save_store(fs(), local_store())
        self.assertEqual(db_files_internal_empty(), actual)

    def test_save_store___on_empty_fs_with_input_store_internal_a___stores_internal_a(self):
        actual = save_store(fs(), local_store(store_internal_a()))
        self.assertEqual(db_files_internal_a(), actual)

    def test_save_store__on_internal_a_with_input_store_empty___stores_internal_empty(self):
        actual = save_store(fs(files=db_files_internal_a()), local_store())
        self.assertEqual(db_files_internal_empty(), actual)

    def test_save_store___on_internal_empty_with_input_store_internal_a___stores_internal_a(self):
        actual = save_store(fs(files=db_files_internal_empty()), local_store(store_internal_a()))
        self.assertEqual(db_files_internal_a(), actual)

    def test_save_store___on_empty_fs_with_input_store_usb0_b_internal_a___stores_internal_a_usb0_b(self):
        actual = save_store(fs(), local_store(store_usb0_b_internal_a()))
        self.assertEqual(db_files_internal_a_usb0_b(), actual)

    def test_save_store___on_internal_a_usb0_b_with_input_store_empty___stores_internal_empty(self):
        actual = save_store(fs(files=db_files_internal_a_usb0_b()), local_store())
        self.assertEqual(db_files_internal_empty(), actual)

    def test_save_store___on_empty_fs_with_input_store_usb0_b_games_internal_a_docs___stores_internal_a_docs_usb0_b_games(self):
        actual = save_store(fs(), local_store(store_usb0_b_games_internal_a_docs()))
        self.assertEqual(db_files_internal_a_docs_usb0_b_games(), actual)

    def test_save_store___on_internal_a_docs_usb0_b_games_with_input_store_empty___stores_internal_empty(self):
        actual = save_store(fs(files=db_files_internal_a_docs_usb0_b_games()), local_store())
        self.assertEqual(db_files_internal_empty(), actual)

    def test_load_store___on_empty_fs___returns_blank_store(self):
        store = load_store(fs())
        self.assertEqual({}, store)

    def test_load_store___on_internal_empty___returns_blank_store(self):
        store = load_store(fs(files=db_files_internal_empty()))
        self.assertEqual({}, store)

    def test_load_store___on_internal_a___returns_store_internal_a(self):
        store = load_store(fs(files=db_files_internal_a()))
        self.assertEqual(store_internal_a(), store)

    def test_load_store___on_internal_a_usb0_b___returns_store_usb0_b_internal_a(self):
        store = load_store(fs(files=db_files_internal_a_usb0_b()))
        self.assertEqual(store_usb0_b_internal_a(), store)

    def test_load_store___on_internal_a_docs_usb0_b_games___returns_store_usb0_b_games_internal_a_docs(self):
        store = load_store(fs(files=db_files_internal_a_docs_usb0_b_games()))
        self.assertEqual(store_usb0_b_games_internal_a_docs(), store)

    def test_load_store___on_empty_internal_but_usb0_birdybro_db___returns_birdy_store_with_fixed_files_and_folders(self):
        store = load_store(fs(files={usb0_db_json_file: birdy_cifs_json_db()}))
        self.assertEqual(birdy_store_with_fixed_files_and_folders(), store)


def save_store(fs_objects, input_local_store):
    file_system, fs_state = fs_objects
    sut = LocalRepository(config=fs_state.config, file_system=file_system)
    local_store_wrapper = LocalStoreWrapper(input_local_store)
    local_store_wrapper.mark_force_save()
    sut.save_store(local_store_wrapper)
    files = {}
    for file_path, file_description in file_system.data['files'].items():
        if 'last_successful_run' in file_path:
            continue

        files[file_path] = file_system.load_dict_from_file(file_path)['dbs']
    return files


def load_store(fs_objects):
    file_system, fs_state = fs_objects
    sut = LocalRepository(config=fs_state.config, file_system=file_system)
    return sut.load_store().unwrap_local_store()['dbs']


def fs(files=None, folders=None):
    files = files if files is not None else {}
    fs_state = FileSystemState(files={file_path: file_descr(hash_code=file_path) for file_path in files}, folders=folders, base_system_path=MEDIA_FAT)
    file_system = FileSystemFactory(state=fs_state).create_for_system_scope()

    for file_path, dbs in files.items():
        store = local_store(dbs, internal=not file_path.startswith('/media/usb'))
        if FILE_downloader_storage.lower() in file_path:
            file_system.save_json_on_zip(store, file_path)
        else:
            file_system.save_json(store, file_path)

    return [file_system, fs_state]


def local_store(dbs=None, internal=True):
    result_local_store = make_new_local_store(StoreMigrator())
    result_local_store['dbs'] = {} if dbs is None else dbs
    result_local_store['internal'] = internal
    return result_local_store


def store_to_db_files(store, base_path=None):
    result = {}
    if base_path is None:
        base_path = MEDIA_FAT
    result[base_path] = {}
    for db_id, store in store.items():
        for drive, external in store['external'].items():
            if drive not in result:
                result[drive] = {}
            result[drive][db_id] = external
        result[base_path][db_id] = {**store}
        del result[base_path][db_id]['external']

    return result


def birdy_store_with_fixed_files_and_folders():
    return {
        'theypsilon_unofficial_distribution': {
            'external': {
                '/media/usb0': {
                    'files': {},
                    'folders': {'games': {}, 'games/hbmame': {}, 'games/mame': {}}
                }
            },
            'files': {},
            'folders': {},
            'offline_databases_imported': [],
            'zips': {}
        }
    }


def birdy_cifs_json_db(): return json.loads('''
{
    "theypsilon_unofficial_distribution": {
        "files": {},
        "folders": {
            "games": {},
            "games/hbmame": {},
            "games/mame": {}
        }
    }
}''')
