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

from downloader.db_options import DbOptionsValidationException, DbOptions
from test.objects import db_options


class TestDbOptions(unittest.TestCase):

    def test_construct_db_options___with_correct_props___returns_options(self):
        self.assertIsNotNone(db_options())

    def test_construct_db_options___with_empty_props___returns_empty_options(self):
        self.assertEqual({}, DbOptions({}).testable)

    def test_construct_db_options___with_not_recognised_option___raises_db_options_validation_exception(self):
        self.assertRaises(DbOptionsValidationException, lambda: DbOptions({'wrong': 'option'}))

    def test_construct_db_options___with_option_base_path___raises_nothing_by_now(self):
        self.assertIsNotNone(DbOptions({'base_path': 'something'}))

