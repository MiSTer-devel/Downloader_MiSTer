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
from test.fakes import Runner, NoLogger
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
