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

    def test_migrate___on_v0_filled_store___returns_expected_store(self):
        store = load_file('test/integration/fixtures/filled_store_v0.json')
        sut = StoreMigrator()
        sut.migrate(store)
        self.assertEqual(store, load_file('test/integration/fixtures/filled_store_vlast.json'))

    def test_migrate___on_v1_filled_store___returns_expected_store(self):
        store = load_file('test/integration/fixtures/filled_store_v1_with_zip.json')
        sut = StoreMigrator()
        sut.migrate(store)
        self.assertEqual(store, load_file('test/integration/fixtures/filled_store_vlast_with_zip.json'))


def load_file(path):
    with open(path) as f:
        return json.load(f)
