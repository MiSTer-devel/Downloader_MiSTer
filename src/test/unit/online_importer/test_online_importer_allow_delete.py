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

from unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from downloader.config import AllowDelete

from test.objects import store_test_with_file_a_descr, config_with, file_a, file_a_descr, folder_a, \
    db_test_being_empty_descr, empty_test_store, store_with_folders, store_test_with_x_rbf_descr, file_x_rbf, \
    file_x_rbf_descr, folder_x
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data


class TestOnlineImporterAllowDelete(OnlineImporterTestBase):
    def test_file_a_removed_from_db___on_allow_delete_all___updates_store_and_deletes_all(self):
        store = store_test_with_file_a_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.ALL, files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [])

    def test_rbf_removed_from_db___on_allow_delete_all___updates_store_and_deletes_all(self):
        store = store_test_with_x_rbf_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.ALL, files={file_x_rbf: file_x_rbf_descr()}, folders=[folder_x]))

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [])

    def test_file_a_removed_from_db___on_allow_delete_none___updates_only_file_in_store_and_deletes_nothing(self):
        store = store_test_with_file_a_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.NONE, files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_with_folders([folder_a]), store)
        self.assertReports(sut, [])

    def test_rbf_removed_from_db___on_allow_delete_none___updates_only_file_in_store_and_deletes_nothing(self):
        store = store_test_with_x_rbf_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.NONE, files={file_x_rbf: file_x_rbf_descr()}, folders=[folder_x]))

        self.assertEqual(fs_data(files={file_x_rbf: file_x_rbf_descr()}, folders=[folder_x]), sut.fs_data)
        self.assertEqual(store_with_folders([folder_x]), store)
        self.assertReports(sut, [])

    def test_file_a_removed_from_db___on_allow_delete_old_rbf___updates_only_file_in_store_and_deletes_nothing(self):
        store = store_test_with_file_a_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.OLD_RBF, files={file_a: file_a_descr()}, folders=[folder_a]))

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_with_folders([folder_a]), store)
        self.assertReports(sut, [])

    def test_rbf_removed_from_db___on_allow_delete_old_rbf___updates_store_and_deletes_file_but_not_folder(self):
        store = store_test_with_x_rbf_descr()

        sut = self.download_empty_db_test(store, fs(ad=AllowDelete.OLD_RBF, files={file_x_rbf: file_x_rbf_descr()}, folders=[folder_x]))

        self.assertEqual(fs_data(folders=[folder_x]), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [])


    def download_empty_db_test(self, store, fs_inputs):
        return self._download_db(db_test_being_empty_descr(), store, fs_inputs)


def fs(files=None, folders=None, ad=None):
    return ImporterImplicitInputs(files=files, folders=folders, config=config_with(allow_delete=ad))
