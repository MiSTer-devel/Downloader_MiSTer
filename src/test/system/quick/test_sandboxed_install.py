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
import shutil
import os
import json
from pathlib import Path
from downloader.config import ConfigReader
from test.objects import debug_env
from test.fakes import NoLogger, StoreMigrator
from downloader.file_service import hash_file, FileService
from downloader.main import main
from downloader.local_repository import LocalRepository
from downloader.store_migrator import make_new_local_store


class TestSandboxedInstall(unittest.TestCase):
    sandbox_ini = "test/system/fixtures/sandboxed_install/sandbox.ini"
    sandbox_db_json = 'test/system/fixtures/sandboxed_install/sandbox_db.json'
    tmp_delme = '/tmp/delme_sandbox/'

    foo_file = 'test/system/fixtures/sandboxed_install/files/foo.txt'
    bar_file = 'test/system/fixtures/sandboxed_install/files/bar.txt'
    baz_file = 'test/system/fixtures/sandboxed_install/files/baz.txt'

    def setUp(self) -> None:
        cleanup(self.sandbox_ini)

    def test_sandbox_db___installs_correctly(self):
        db = load_json(self.sandbox_db_json)
        self.assertExecutesCorrectly(self.sandbox_ini, {
            'local_store': local_store_files([('sandbox', db['files'])]),
            'files': hashes(self.tmp_delme, db['files'])
        })

    def test_sandbox_db___installs_correctly__twice(self):
        db = load_json(self.sandbox_db_json)
        self.assertExecutesCorrectly(self.sandbox_ini)
        self.assertExecutesCorrectly(self.sandbox_ini, {
            'local_store': local_store_files([('sandbox', db['files'])]),
            'files': hashes(self.tmp_delme, db['files'])
        })

    def test_sandbox_db___deletes_one_installed_file_on_second_call(self):
        self.assertExecutesCorrectly(self.sandbox_ini, {
            'files_count': 2
        })

        minus_one_file_db = load_json('test/system/fixtures/sandboxed_install/minus_one_file/sandbox_db.json')
        self.assertExecutesCorrectly("test/system/fixtures/sandboxed_install/minus_one_file/sandbox.ini", {
            'local_store': local_store_files([('sandbox', minus_one_file_db['files'])]),
            'files': hashes(self.tmp_delme, minus_one_file_db['files']),
            'files_count': 1
        })

    def test_sandbox_db___updates_one_installed_file_on_second_call(self):
        db = load_json(self.sandbox_db_json)
        self.assertExecutesCorrectly(self.sandbox_ini, {
            'files': hashes(self.tmp_delme, db['files']),
        })

        updated_db = load_json('test/system/fixtures/sandboxed_install/updated_file/sandbox_db.json')
        self.assertExecutesCorrectly("test/system/fixtures/sandboxed_install/updated_file/sandbox.ini", {
            'files': hashes(self.tmp_delme, updated_db['files']),
        })

        self.assertNotEqual(db['files']['bar.txt']['hash'], updated_db['files']['bar.txt']['hash'])

    def test_sandbox_db___updates_only_existing_files_that_changed(self):
        tmp_foo_file = self.tmp_delme + '/foo.txt'
        tmp_bar_file = self.tmp_delme + '/bar.txt'

        Path(tmp_foo_file).touch()
        shutil.copy2(self.bar_file, self.tmp_delme)

        foo_hash_before = hash_file(tmp_foo_file)
        bar_hash_before = hash_file(tmp_bar_file)

        db = load_json(self.sandbox_db_json)
        self.assertExecutesCorrectly(self.sandbox_ini, {
            'local_store': local_store_files([('sandbox', db['files'])]),
            'files': hashes(self.tmp_delme, db['files'])
        })

        foo_hash_after = hash_file(tmp_foo_file)
        bar_hash_after = hash_file(tmp_bar_file)

        self.assertNotEqual(foo_hash_before, foo_hash_after)
        self.assertEqual(bar_hash_before, bar_hash_after)

    def test_sandbox_db___doesnt_remove_unhandled_extra_file_by_default(self):
        shutil.copy2(self.foo_file, self.tmp_delme)
        shutil.copy2(self.bar_file, self.tmp_delme)
        shutil.copy2(self.baz_file, self.tmp_delme)

        baz_exists_before = Path(self.baz_file).is_file()

        db = load_json(self.sandbox_db_json)
        files_plus_extra = db['files'].copy()
        files_plus_extra['baz.txt'] = {'hash': 'c15bc5117b800187ea76873b5491e1db'}

        self.assertExecutesCorrectly(self.sandbox_ini, {
            'local_store': local_store_files([('sandbox', db['files'])]),
            'files': hashes(self.tmp_delme, files_plus_extra),
            'files_count': 3
        })

        baz_exists_after = Path(self.baz_file).is_file()

        self.assertEqual(baz_exists_before, baz_exists_after)

    def test_sandbox_db___deletes_extra_file_from_offline_db(self):
        sandbox_db_with_extra_json_file = 'test/system/fixtures/sandboxed_install/offline_db_with_extra_file/sandbox_db_with_extra_file.json'

        shutil.copy2(self.foo_file, self.tmp_delme)
        shutil.copy2(self.bar_file, self.tmp_delme)
        shutil.copy2(self.baz_file, self.tmp_delme)
        shutil.copy2(sandbox_db_with_extra_json_file, self.tmp_delme)

        tmp_offline_db_file = self.tmp_delme + '/' + Path(sandbox_db_with_extra_json_file).name
        tmp_baz_file = self.tmp_delme + '/' + Path(self.baz_file).name

        offline_db_exists_before = Path(tmp_offline_db_file).is_file()
        baz_exists_before = Path(tmp_baz_file).is_file()

        db = load_json('test/system/fixtures/sandboxed_install/offline_db_with_extra_file/sandbox_db.json')
        expected_local_store = local_store_files([('sandbox', db['files'])])
        expected_local_store['dbs']['sandbox']['offline_databases_imported'] = ['0627c397ac9d734dfdb86b9c8294eabe']

        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/offline_db_with_extra_file/sandbox.ini', {
            'local_store': expected_local_store,
            'files': hashes(self.tmp_delme, db['files']),
            'files_count': 2
        })

        offline_db_exists_after = Path(tmp_offline_db_file).is_file()
        baz_exists_after = Path(tmp_baz_file).is_file()

        self.assertNotEqual(offline_db_exists_before, offline_db_exists_after)
        self.assertNotEqual(baz_exists_before, baz_exists_after)
        self.assertFalse(offline_db_exists_after or baz_exists_after)

    installed_folders = {'bar': {}, 'bar/sub_bar': {}, 'bar/sub_bar/sub_sub_bar': {}, 'baz': {}, 'foo': {}, 'foo/sub_foo': {}}
    installed_system_folders = {'Scripts': {}, 'Scripts/.config': {}, 'Scripts/.config/downloader': {}}

    def test_sandbox_db___installs_expected_folders(self):
        expected_local_store = local_store_files([('sandbox', {})])
        expected_local_store['dbs']['sandbox']['folders'] = {'foo': {}, 'bar': {}, 'foo/sub_foo': {}, 'bar/sub_bar': {},
                                                      'bar/sub_bar/sub_sub_bar': {}, 'baz': {}}
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_folders/sandbox.ini', {
            'local_store': expected_local_store,
            'folders': self.installed_folders,
            'system_folders': self.installed_system_folders
        })

    def test_sandbox_db___removes_installed_missing_folders(self):
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_folders/sandbox.ini', {
            'folders': self.installed_folders,
            'system_folders': self.installed_system_folders
        })

        remaining_folders = {'bar': {}, 'bar/sub_bar': {}}
        expected_local_store = local_store_files([('sandbox', {})])
        expected_local_store['dbs']['sandbox']['folders'] = remaining_folders
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_less_folders/sandbox.ini', {
            'local_store': expected_local_store,
            'folders': remaining_folders,
            'system_folders': self.installed_system_folders
        })

    def test_sandbox_db___removes_installed_missing_folders_except_when_they_contain_a_file(self):
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_folders/sandbox.ini', {
            'folders': self.installed_folders,
            'system_folders': self.installed_system_folders
        })

        self.file_service.touch('foo/something')
        self.file_service.makedirs('baz/something')

        expected_local_store = local_store_files([('sandbox', {})])
        expected_local_store['dbs']['sandbox']['folders'] = {'bar': {}, 'bar/sub_bar': {}}
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_less_folders/sandbox.ini', {
            'local_store': expected_local_store,
            'folders': {'bar': {}, 'bar/sub_bar': {}, 'baz': {}, 'baz/something': {}, 'foo': {}},
            'system_folders': self.installed_system_folders
        })

    def assertExecutesCorrectly(self, ini_path, expected=None):
        self.maxDiff = None
        exit_code = self.run_main(ini_path)
        self.assertEqual(exit_code, 0)

        if expected is None:
            return

        config = ConfigReader(NoLogger(), debug_env()).read_config(ini_path)
        self.file_service = FileService(config, NoLogger())
        counter = 0
        if 'local_store' in expected:
            counter += 1
            actual_store = LocalRepository(config, NoLogger(), self.file_service).load_store(StoreMigrator())
            self.assertEqual(actual_store, expected['local_store'])

        if 'files' in expected:
            counter += 1
            self.assertEqual(self.find_all_files(config['base_path']), expected['files'])

        if 'files_count' in expected:
            counter += 1
            self.assertEqual(len(self.find_all_files(config['base_path'])), expected['files_count'])

        if 'system_files' in expected:
            counter += 1
            self.assertEqual(self.find_all_files(config['base_system_path']), expected['system_files'])

        if 'system_files_count' in expected:
            counter += 1
            self.assertEqual(len(self.find_all_files(config['base_path'])), expected['system_files_count'])

        if 'folders' in expected:
            counter += 1
            self.assertEqual(self.find_all_folders(config['base_path']), sorted(list(expected['folders'])))

        if 'system_folders' in expected:
            counter += 1
            self.assertEqual(self.find_all_folders(config['base_system_path']), sorted(list(expected['system_folders'])))

        self.assertEqual(counter, len(expected))

    @staticmethod
    def run_main(ini_path):
        return main({
            'DOWNLOADER_LAUNCHER_PATH': str(Path(ini_path).with_suffix('.sh')),
            'CURL_SSL': '',
            'UPDATE_LINUX': 'false',
            'ALLOW_REBOOT': None,
            'COMMIT': 'quick system test',
            'DEFAULT_DB_URL': '',
            'DEFAULT_DB_ID': '',
            'DEBUG': 'true'
        })

    def find_all_files(self, directory):
        return sorted(self._scan_files(directory), key=lambda t: t[0].lower())

    def _scan_files(self, directory):
        for entry in os.scandir(directory):
            if entry.is_dir(follow_symlinks=False):
                yield from self._scan_files(entry.path)
            else:
                yield entry.path, hash_file(entry.path)

    def find_all_folders(self, directory):
        if not directory.endswith('/'):
            directory = directory + '/'
        return sorted(self._scan_folders(directory, directory), key=str.casefold)

    def _scan_folders(self, directory, base):
        for entry in os.scandir(directory):
            if entry.is_dir(follow_symlinks=False):
                yield from self._scan_folders(entry.path, base)
                yield entry.path[len(base):]


def cleanup(ini_path):
    config = ConfigReader(NoLogger(), debug_env()).read_config(ini_path)
    shutil.rmtree(config['base_path'], ignore_errors=True)
    shutil.rmtree(config['base_system_path'], ignore_errors=True)
    Path(config['base_path']).mkdir(parents=True, exist_ok=True)
    Path(config['base_system_path']).mkdir(parents=True, exist_ok=True)


def local_store_files(tuples):
    store = make_new_local_store(StoreMigrator())
    for store_id, files in tuples:
        store['dbs'][store_id] = {
                'folders': {},
                'files': files,
                'offline_databases_imported': [],
                'zips': {}
            }
    return store


def hashes(base_path, files):
    return sorted([(base_path + f, files[f]['hash']) for f in files])


def load_json(file_path):
    with open(file_path, "r") as f:
        return json.loads(f.read())
