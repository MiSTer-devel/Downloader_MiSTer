# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from unittest.mock import Mock, MagicMock

from downloader.config import UpdateLinuxEnvironment
from test.fake_full_run_service import FullRunService
from test.objects import raw_db_empty_descr, raw_db_empty_with_linux_descr, raw_db_wrong_descr, db_empty


class TestFullRunService(unittest.TestCase):
    def test_full_run___no_databases___returns_0(self):
        exit_code = FullRunService.with_no_dbs().full_run()
        self.assertEqual(exit_code, 0)

    def test_full_run___empty_databases___returns_0(self):
        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_descr()).full_run()
        self.assertEqual(exit_code, 0)

    def test_full_run___database_with_wrong_id___returns_1(self):
        exit_code = FullRunService.with_single_db(db_empty, raw_db_wrong_descr()).full_run()
        self.assertEqual(exit_code, 1)

    def test_full_run___database_not_fetched___returns_1(self):
        exit_code = FullRunService.with_single_empty_db().full_run()
        self.assertEqual(exit_code, 1)

    def test_full_run___database_with_new_linux___calls_update_linux_and_returns_0(self):
        linux_updater = Mock()
        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_with_linux_descr(), linux_updater=linux_updater).full_run()
        self.assertEqual(exit_code, 0)
        linux_updater.update_linux.assert_called()

    def test_full_run___database_with_new_linux_and_linux_update_environment_only___calls_update_linux_and_returns_0(self):
        linux_updater = Mock()
        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_with_linux_descr(), linux_updater=linux_updater, linux_update_environment=UpdateLinuxEnvironment.ONLY).full_run()
        self.assertEqual(exit_code, 0)
        linux_updater.update_linux.assert_called()

    def test_full_run___database_with_old_linux_and_linux_update_environment_only___calls_update_linux_and_returns_0(self):
        linux_updater = Mock()
        linux_updater.needs_reboot.return_value = False
        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_with_linux_descr(), linux_updater=linux_updater, linux_update_environment=UpdateLinuxEnvironment.ONLY).full_run()
        self.assertEqual(exit_code, 0)
        linux_updater.update_linux.assert_called()

    def test_full_run___database_with_nwe_linux_and_linux_update_disabled_but_environment_only___doesnt_call_update_linux_and_returns_0(self):
        linux_updater = Mock()
        exit_code = FullRunService.with_single_db(db_empty,
                                                  raw_db_empty_with_linux_descr(),
                                                  linux_updater=linux_updater,
                                                  linux_update_environment=UpdateLinuxEnvironment.ONLY,
                                                  update_linux=False
                                                  ).full_run()
        self.assertEqual(exit_code, 0)
        linux_updater.update_linux.assert_not_called()
