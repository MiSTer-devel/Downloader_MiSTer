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
from test.fakes import Runner
from test.objects import db_empty_descr, db_empty_with_linux_descr, db_wrong_descr, db_empty


class TestRunner(unittest.TestCase):
    def test_run___no_databases___returns_0(self):
        exit_code = Runner.with_no_dbs().run()
        self.assertEqual(exit_code, 0)

    def test_run___empty_databases___returns_0(self):
        exit_code = Runner.with_single_db(db_empty, db_empty_descr()).run()
        self.assertEqual(exit_code, 0)

    def test_run___database_with_new_linux___returns_0(self):
        exit_code = Runner.with_single_db(db_empty, db_empty_with_linux_descr()).run()
        self.assertEqual(exit_code, 0)

    def test_run___database_with_wrong_id___returns_1(self):
        exit_code = Runner.with_single_db(db_empty, db_wrong_descr()).run()
        self.assertEqual(exit_code, 1)

    def test_run___database_not_fetched___returns_1(self):
        exit_code = Runner.with_single_empty_db().run()
        self.assertEqual(exit_code, 1)

    def test_validate_db___with_correct_db___returns_true(self):
        self.assertTrue(validate_db())

    def test_validate_db___with_wrong_section___returns_false(self):
        self.assertFalse(validate_db(db_description={'section': ''}))

    def test_validate_db___with_wrong_db___returns_false(self):
        self.assertFalse(validate_db(db="wrong"))

    def test_validate_db___with_none_db___returns_false(self):
        self.assertFalse(Runner.with_single_empty_db().validate_db(None, {}))

    def test_validate_db___with_wrong_field___returns_false(self):
        for field in ['db_id', 'base_files_url', 'db_files', 'files', 'folders', 'zips', 'default_options', 'timestamp']:
            with self.subTest(field):
                db = db_empty_descr()
                db.pop(field)
                self.assertFalse(validate_db(db))


def validate_db(db=None, db_description=None):
    return Runner.with_single_empty_db().validate_db(db_empty_descr() if db is None else db, db_empty if db_description is None else db_description['section'])
