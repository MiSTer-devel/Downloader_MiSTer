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
import os
import shutil
from pathlib import Path
from downloader.constants import K_BASE_PATH, FILE_mister_downloader_needs_reboot
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.logger import PrintLogger, TopLogger
from test.fake_logger import NoLogger
from test.system.quick.sandbox_test_base import SandboxTestBase, tmp_delme_sandbox, local_store_files, load_json, hashes, cleanup
from test.fake_store_migrator import StoreMigrator
from downloader.file_system import hash_file


class TestSandboxedInstall(SandboxTestBase):
    sandbox_ini = "test/system/fixtures/sandboxed_install/sandbox.ini"
    sandbox_db_json = 'test/system/fixtures/sandboxed_install/sandbox_db.json'

    tmp_delme = tmp_delme_sandbox

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

    def test_sandbox_db_with_single_db___runs_correctly(self):
        single_db_sandbox_ini = 'test/system/fixtures/sandboxed_install/single_db/sandbox.ini'
        cleanup(single_db_sandbox_ini)
        self.assertExecutesCorrectly(single_db_sandbox_ini)

    def test_sandbox_db_with_delete_previous___installs_correctly(self):
        db = load_json('test/system/fixtures/sandboxed_install/db_with_delete_previous/sandbox_db.json')
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_delete_previous/sandbox.ini', {
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

        tmp_bar_file = self.tmp_delme + '/baz.txt'

        baz_exists_before = Path(tmp_bar_file).is_file()

        db = load_json(self.sandbox_db_json)
        files_plus_extra = db['files'].copy()
        files_plus_extra['baz.txt'] = {'hash': 'c15bc5117b800187ea76873b5491e1db'}

        self.assertExecutesCorrectly(self.sandbox_ini, {
            'local_store': local_store_files([('sandbox', db['files'])]),
            'files': hashes(self.tmp_delme, files_plus_extra),
            'files_count': 3
        })

        baz_exists_after = Path(tmp_bar_file).is_file()

        self.assertEqual(baz_exists_before, baz_exists_after)

    installed_folders = {'bar': {}, 'bar/sub_bar': {}, 'bar/sub_bar/sub_sub_bar': {}, 'baz': {}, 'foo': {},
                         'foo/sub_foo': {}}
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

        self.file_system.touch('foo/something')
        self.file_system.make_dirs('baz/something')

        expected_local_store = local_store_files([('sandbox', {})])
        expected_local_store['dbs']['sandbox']['folders'] = {'bar': {}, 'bar/sub_bar': {}, 'baz': {}, 'foo': {}}
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/db_with_less_folders/sandbox.ini', {
            'local_store': expected_local_store,
            'folders': {'bar': {}, 'bar/sub_bar': {}, 'baz': {}, 'baz/something': {}, 'foo': {}},
            'system_folders': self.installed_system_folders
        })

    def test_sandbox_db___relocates_files_after_base_path_changed_in_ini(self):
        self.assertExecutesCorrectly(self.sandbox_ini)

        self.assertTrue(Path('/tmp/delme_sandbox/foo.txt').is_file())

        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/relocated_db/sandbox.ini', {
            'local_store': {
                'db_sigs': {},
                'dbs': {
                    'sandbox': {
                        K_BASE_PATH: '/tmp/delme_relocated',
                        'files': {
                            'bar.txt': {'delete': [], 'hash': '942b89ab661f86228ea9ad3e980763a7', 'size': 4, 'url': 'https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/src/test/system/fixtures/sandboxed_install/files/bar.txt'},
                            'foo.txt': {'delete': [], 'hash': '133af32b4894d9c5527cc5c91269ee28', 'size': 20, 'url': 'https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/src/test/system/fixtures/sandboxed_install/files/foo.txt'}},
                        'folders': {},
                        'zips': {}
                    }
                },
                'migration_version': StoreMigrator().latest_migration_version(),
                'internal': True
            },
        })

        self.assertFalse(Path('/tmp/delme_sandbox/foo.txt').is_file())
        self.assertTrue(Path('/tmp/delme_relocated/foo.txt').is_file())

    def test_small_db_3(self):
        self.assertExecutesCorrectly("test/system/fixtures/small_db_install/small_db_3.ini")
        self.assertFalse(os.path.isfile(FILE_mister_downloader_needs_reboot))

    def test_print_drives(self):
        logger = TopLogger(PrintLogger(), NoLogger())
        exit_code = self.run_execute_full_run(self.sandbox_ini, ExternalDrivesRepositoryFactory(), logger, logger, ['', '--print-drives'])
        self.assertEqual(0, exit_code)

    def test_sandbox_db___installs_file_after_applying_expanded_filter(self):
        self.assertExecutesCorrectly('test/system/fixtures/sandboxed_install/filter_inheritance/expanded_mister_filter.ini', {
            'files': hashes(self.tmp_delme, {
                'GB.rbf': {'hash': '942b89ab661f86228ea9ad3e980763a7'},
                'SNES.rbf': {'hash': '133af32b4894d9c5527cc5c91269ee28'},
            }),
        })
