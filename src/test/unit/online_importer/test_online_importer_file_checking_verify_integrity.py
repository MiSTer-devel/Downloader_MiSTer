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

from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects import file_a_descr, file_a, folder_a, store_test_with_file_a_descr, db_test_with_file_a, config_with
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from downloader.config import FileChecking


class TestOnlineImporterFileCheckingVerifyIntegrity(OnlineImporterTestBase):

    def test_download_one_file___after_previous_identical_run___verifies_successfully_that_file_and_nothing_else(self):
        store = store_test_with_file_a_descr()

        sut = self._download_db(db_test_with_file_a(), store, fs(files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False, verified_files=[file_a])

    def test_download_one_file___after_previous_identical_run___catches_corrupt_file_and_installs_it_again(self):
        store = store_test_with_file_a_descr()

        sut = self._download_db(db_test_with_file_a(), store, fs(files={file_a: file_a_descr(file_hash='wrong')}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False, verified_files=[])

def fs(files=None, folders=None):
    return ImporterImplicitInputs(
        files=files,
        folders=folders,
        config=config_with(file_checking=FileChecking.VERIFY_INTEGRITY)
    )
