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
import json

from downloader.constants import K_BASE_PATH, DISTRIBUTION_MISTER_DB_ID
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_file_system_factory import fs_data, FileSystemFactory
from test.objects import file_descr
from test.fake_store_migrator import StoreMigrator


class TestRealisticMigrations(unittest.TestCase):

    filled_store_v0 = 'test/integration/fixtures/filled_store_v0.json'
    filled_store_v0_with_uppercase_db_id = 'test/integration/fixtures/filled_store_v0_with_uppercase_db_id.json'
    filled_store_v7_with_root_base_path = 'test/integration/fixtures/filled_store_v7_with_root_base_path.json'
    filled_store_v7_with_oldschool_base_path = 'test/integration/fixtures/filled_store_v7_with_oldschool_base_path.json'
    filled_store_vlast = 'test/integration/fixtures/filled_store_vlast.json'

    filled_store_v1_with_zip = 'test/integration/fixtures/filled_store_v1_with_zip.json'
    filled_store_vlast_with_zip = 'test/integration/fixtures/filled_store_vlast_with_zip.json'

    empty_store_external_v9 = 'test/integration/fixtures/empty_store_external_v9.json'
    empty_store_external_vlast = 'test/integration/fixtures/empty_store_external_vlast.json'

    def test_migrate___on_v0_filled_store___returns_expected_store(self):
        self.assert_versions_change_as_expected(self.filled_store_v0, self.filled_store_vlast)

    def test_migrate___on_v0_filled_store_with_uppercase_db_id___returns_expected_store(self):
        self.assert_versions_change_as_expected(self.filled_store_v0_with_uppercase_db_id, self.filled_store_vlast)

    def test_migrate___on_vlast_filled_store___returns_same_store(self):
        self.assert_versions_stay_the_same(self.filled_store_vlast)

    def test_migrate___on_v7_filled_store_with_oldschool_base_path___returns_expected_store(self):
        self.assert_versions_change_as_expected(self.filled_store_v7_with_oldschool_base_path, self.filled_store_vlast)

    def test_migrate___on_v7_filled_store_with_root_base_path___returns_same_base_path_as_in_v7(self):
        store = load_file(self.filled_store_v7_with_root_base_path)
        v7_base_path = store['dbs'][DISTRIBUTION_MISTER_DB_ID][K_BASE_PATH]

        StoreMigrator().migrate(store)
        self.assertEqual(v7_base_path, store['dbs'][DISTRIBUTION_MISTER_DB_ID][K_BASE_PATH])

    def test_migrate___on_v9_empty_store_external___returns_expected_store(self):
        self.assert_versions_change_as_expected(self.empty_store_external_v9, self.empty_store_external_vlast)

    def test_migrate___on_v1_with_zip_filled_store___returns_expected_store(self):
        self.assert_versions_change_as_expected(self.filled_store_v1_with_zip, self.filled_store_vlast_with_zip)

    def test_migrate___on_vlast_with_zip_filled_store___returns_same_store(self):
        self.assert_versions_stay_the_same(self.filled_store_vlast_with_zip)

    def test_migrate___from_v10_to_v11_with_old_pext_paths_and_filters_covering_zips_and_non_zips_scenarios___returns_expected_store(self):
        self.assertTrue(False)

    def assert_versions_change_as_expected(self, initial_file, expected_file):
        store = load_file(initial_file)
        StoreMigrator().migrate(store)
        self.assertEqual(set_latest_migration_version(load_file(expected_file)), store)

    def assert_versions_stay_the_same(self, file):
        store = set_latest_migration_version(load_file(file))
        StoreMigrator().migrate(store)
        self.assertEqual(set_latest_migration_version(load_file(file)), store)


def load_file(path):
    with open(path) as f:
        return json.load(f)


def set_latest_migration_version(store):
    result = store.copy()
    result['migration_version'] = StoreMigrator().latest_migration_version()
    return result
