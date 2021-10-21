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
import json
from test.fakes import StoreMigrator


class TestRealisticMigrations(unittest.TestCase):

    filled_store_v0 = 'test/integration/fixtures/filled_store_v0.json'
    filled_store_vlast = 'test/integration/fixtures/filled_store_vlast.json'

    filled_store_v1_with_zip = 'test/integration/fixtures/filled_store_v1_with_zip.json'
    filled_store_vlast_with_zip = 'test/integration/fixtures/filled_store_vlast_with_zip.json'


    def test_migrate___on_v0_filled_store___returns_expected_store(self):
        store = load_file(self.filled_store_v0)
        StoreMigrator().migrate(store)
        self.assertEqual(store, load_file(self.filled_store_vlast))

    def test_migrate___on_vlast_filled_store___returns_same_store(self):
        store = load_file(self.filled_store_vlast)
        StoreMigrator().migrate(store)
        self.assertEqual(store, load_file(self.filled_store_vlast))

    def test_migrate___on_v1_with_zip_filled_store___returns_expected_store(self):
        store = load_file(self.filled_store_v1_with_zip)
        StoreMigrator().migrate(store)
        self.assertEqual(store, load_file(self.filled_store_vlast_with_zip))

    def test_migrate___on_vlast_with_zip_filled_store___returns_same_store(self):
        store = load_file(self.filled_store_vlast_with_zip)
        StoreMigrator().migrate(store)
        self.assertEqual(store, load_file(self.filled_store_vlast_with_zip))


def load_file(path):
    with open(path) as f:
        return json.load(f)
