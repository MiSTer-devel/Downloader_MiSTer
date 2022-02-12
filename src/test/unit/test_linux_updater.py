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

from downloader.constants import FILE_MiSTer_version
from test.factory_stub import FactoryStub
from test.fake_linux_updater import LinuxUpdater
from test.objects import db_entity
from test.fake_file_downloader import FileDownloader


class TestLinuxUpdater(unittest.TestCase):

    def setUp(self):
        self.sut = LinuxUpdater()

    def test_update_linux___no_databases___no_need_to_reboot(self):
        self.sut.update()
        self.assertFalse(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "unknown")

    def test_update_linux___no_linux_databases___no_need_to_reboot(self):
        self.sut.add_db(db_entity(db_id='first'))
        self.sut.add_db(db_entity(db_id='second'))
        self.sut.update()
        self.assertFalse(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "unknown")

    def test_update_linux___db_with_new_linux___has_new_version_and_needs_reboot(self):
        self.sut.add_db(db_entity(db_id='new', linux=linux_description()))
        self.sut.update()
        self.assertTrue(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "210711")

    def test_update_linux___db_with_old_linux___has_old_version_and_no_need_to_reboot(self):
        self.sut.file_system.test_data.with_file(FILE_MiSTer_version, {'content': "210711"})
        self.sut.add_db(db_entity(db_id='new', linux=linux_description()))
        self.sut.update()
        self.assertFalse(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "210711")

    def test_update_linux___dbs_with_different_new_linux___updates_first_linux_and_needs_reboot(self):
        self.sut.add_db(db_entity(db_id='new_2', linux=linux_description_with_version("222222")))
        self.sut.add_db(db_entity(db_id='new_1', linux=linux_description_with_version("111111")))
        self.sut.add_db(db_entity(db_id='new_3', linux=linux_description_with_version("333333")))
        self.sut.update()
        self.assertTrue(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "222222")

    def test_update_linux___new_linux_but_failed_download___no_need_to_reboot(self):
        self.sut = LinuxUpdater(FactoryStub(FileDownloader()).has(lambda fd: fd.test_data.errors_at('linux.7z')))
        self.sut.add_db(db_entity(db_id='new', linux=linux_description()))
        self.sut.update()
        self.assertFalse(self.sut.needs_reboot())
        self.assertEqual(self.sut.file_system.read_file_contents(FILE_MiSTer_version), "unknown")


def linux_description():
    return linux_description_with_version("210711")


def linux_description_with_version(version):
    return {
        "delete": [],
        "hash": "d3b619c54c4727ab618bf108013f79d9",
        "size": 83873790,
        "url": linux_url,
        "version": version
    }


linux_url = "https://raw.githubusercontent.com/MiSTer-devel/SD-Installer-Win64_MiSTer/136d7d8ea24b1de2424574b2d31f527d6b3e3d39/release_20210711.rar"
