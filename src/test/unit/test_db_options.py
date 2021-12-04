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

from downloader.db_options import DbOptionsValidationException, DbOptions, DbOptionsKind
from test.objects import db_options


props_base_path = {'base_path': 'something'}


class TestDbOptions(unittest.TestCase):

    props_with_bad_calls = [
        ('base_path', lambda: db_options(base_path=False)),
        ('update_linux', lambda: db_options(update_linux='false')),
        ('parallel_update', lambda: db_options(parallel_update=0)),
        ('downloader_size_mb_limit', lambda: db_options(downloader_size_mb_limit=-10)),
        ('downloader_process_limit', lambda: db_options(downloader_process_limit=False)),
        ('downloader_timeout', lambda: db_options(downloader_timeout='1')),
        ('downloader_retries', lambda: db_options(downloader_retries=0)),
    ]

    def test_construct_db_options___with_correct_props___returns_options(self):
        self.assertIsNotNone(db_options())

    def test_construct_db_options___with_empty_props___returns_empty_options(self):
        for kind in [DbOptionsKind.DEFAULT_OPTIONS, DbOptionsKind.INI_SECTION]:
            with self.subTest(kind.name):
                self.assertEqual({}, DbOptions({}, kind=kind).testable)

    def test_construct_db_options___with_wrong_incorrect_option___raises_db_options_validation_exception(self):
        for prop, bad_call in self.props_with_bad_calls:
            with self.subTest(prop):
                self.assertRaises(DbOptionsValidationException, bad_call)

    def test_construct_db_options___with_props_in_isolation___returns_options(self):
        for prop, _ in self.props_with_bad_calls:
            with self.subTest(prop):
                expected_prop = {prop: db_options().testable[prop]}
                self.assertIsNotNone(DbOptions(expected_prop, kind=DbOptionsKind.INI_SECTION).testable)

    def test_construct_db_options___with_invalid_kind___raises_value_error(self):
        self.assertRaises(ValueError, lambda: db_options(kind=3))

    def test_construct_db_options___with_not_recognised_option___raises_db_options_validation_exception(self):
        self.assertRaises(DbOptionsValidationException, lambda: DbOptions({'wrong': 'option'}, kind=DbOptionsKind.INI_SECTION))

    def test_construct_db_options___with_kind_default_options_and_base_path___raises_db_options_validation_exception(self):
        self.assertRaises(DbOptionsValidationException, lambda: DbOptions(props_base_path, kind=DbOptionsKind.DEFAULT_OPTIONS))

    def test_construct_db_options___with_kind_ini_section_and_base_path___returns_expected_option(self):
        self.assertEqual(props_base_path, DbOptions(props_base_path, kind=DbOptionsKind.INI_SECTION).testable)
