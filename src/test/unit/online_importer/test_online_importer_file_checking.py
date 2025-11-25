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
from test.objects import file_a_descr, file_a, folder_a, store_test_with_file_a_descr, db_test_with_file_a, config_with, \
    db_test, sig_db_0, sig_db_1
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from downloader.config import FileChecking


class TestOnlineImporterFileChecking(OnlineImporterTestBase):

    def test_download_on_verify_integrity___on_installed_db___verifies_successfully_that_file_and_nothing_else(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.VERIFY_INTEGRITY, files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False, verified_files=[file_a])

    def test_download_on_verify_integrity___with_corrupt_file_on_installed_db___catches_corrupt_file_and_installs_it_again(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.VERIFY_INTEGRITY, files={file_a: file_a_descr(file_hash='wrong')}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False, verified_files=[])

    def test_download_on_exhaustive___on_installed_db___does_nothing(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.EXHAUSTIVE, files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False)

    def test_download_on_exhaustive___with_removed_file_on_installed_db___installs_it_again(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.EXHAUSTIVE, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False)

    def test_download_on_fastest___with_removed_file_on_installed_db___skips_db_and_does_not_install_missing_file(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.FASTEST, folders=[folder_a]))

        self.assertEqual(fs_data(folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False, skipped_dbs=[db_test])

    def test_download_on_fastest___not_matching_sig_on_installed_db___installs_missing_file_and_saves_store(self):
        store = store_test_with_file_a_descr()

        sut = self.download_db_test(store, fs(fc=FileChecking.FASTEST, folders=[folder_a]), matching_sig=False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=True)

    def download_db_test(self, store, fs_inputs, matching_sig=True):
        db_sig = sig_db_0()
        store_sig = sig_db_0() if matching_sig else sig_db_1()
        return self._download_db(db_test_with_file_a(), store, fs_inputs, store_sig=store_sig, db_sig=db_sig)

def fs(files=None, folders=None, fc=None):
    return ImporterImplicitInputs(files=files, folders=folders, config=config_with(file_checking=fc))
