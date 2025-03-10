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
from test.fake_reboot_calculator import RebootCalculator
from test.fake_file_system_factory import FileSystemFactory
from downloader.config import AllowReboot
from downloader.constants import FILE_mister_downloader_needs_reboot, K_ALLOW_REBOOT


class TestRebootCalculator(unittest.TestCase):

    def test_calc_needs_reboot___when_nothing_needs_reboot___returns_false_and_doesnt_create_reboot_file(self):
        fs = FileSystemFactory().create_for_system_scope()
        actual = RebootCalculator(file_system=fs).calc_needs_reboot(False, False)
        self.assertFalse(actual)
        self.assertFalse(fs.is_file(FILE_mister_downloader_needs_reboot))

    def test_calc_needs_reboot___when_linux_needs_reboot___returns_true(self):
        actual = RebootCalculator().calc_needs_reboot(True, False)
        self.assertTrue(actual)

    def test_calc_needs_reboot___when_importer_needs_reboot___returns_true(self):
        actual = RebootCalculator().calc_needs_reboot(False, True)
        self.assertTrue(actual)

    def test_calc_needs_reboot___when_everything_needs_reboot___returns_true(self):
        actual = RebootCalculator().calc_needs_reboot(True, True)
        self.assertTrue(actual)

    def test_calc_needs_reboot___when_no_reboot_config_but_everything_needs_reboot___returns_false_and_creates_reboot_file(self):
        fs = FileSystemFactory().create_for_system_scope()
        actual = RebootCalculator({K_ALLOW_REBOOT: AllowReboot.NEVER}, fs).calc_needs_reboot(True, True)
        self.assertFalse(actual)
        self.assertTrue(fs.is_file(FILE_mister_downloader_needs_reboot))

    def test_calc_needs_reboot___when_only_linux_reboots_and_importer_needs_reboot___returns_false_and_creates_reboot_file(self):
        fs = FileSystemFactory().create_for_system_scope()
        actual = RebootCalculator({K_ALLOW_REBOOT: AllowReboot.ONLY_AFTER_LINUX_UPDATE}, fs).calc_needs_reboot(False, True)
        self.assertFalse(actual)
        self.assertTrue(fs.is_file(FILE_mister_downloader_needs_reboot))

    def test_calc_needs_reboot___when_only_linux_reboots_and_linux_needs_reboot___returns_true(self):
        actual = RebootCalculator({K_ALLOW_REBOOT: AllowReboot.ONLY_AFTER_LINUX_UPDATE}).calc_needs_reboot(True, False)
        self.assertTrue(actual)
