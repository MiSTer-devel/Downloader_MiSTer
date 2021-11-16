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

from downloader.importer_command import ImporterCommand


nil = {}
config = {'x': 'y'}


class TestImporterCommand(unittest.TestCase):

    def test_read_dbs___after_adding_nothing___returns_empty_array(self):
        self.assertEqual([], ImporterCommand(config).read_dbs())

    def test_read_dbs___after_adding_no_options___returns_original_config(self):
        actual = ImporterCommand(config)\
            .add_db(nil, nil, nil)\
            .add_db(nil, nil, nil)\
            .read_dbs()

        self.assertEqual([(nil, nil, config), (nil, nil, config)], actual)

    def test_read_dbs___after_adding_different_options___returns_corresponding_original_config_variants(self):
        actual = ImporterCommand(config)\
            .add_db(nil, nil, {'options': {'a': 'b'}})\
            .add_db(nil, nil, {'options': {'c': 'd'}})\
            .read_dbs()

        self.assertEqual([(nil, nil, {'a': 'b', 'x': 'y'}), (nil, nil, {'c': 'd', 'x': 'y'})], actual)
