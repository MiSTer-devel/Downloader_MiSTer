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
from downloader.other import empty_store
from test.objects import db_test_descr, empty_zip_summary, store_test_descr, empty_test_store
from test.objects import file_a, zipped_file_a_descr, zip_desc
from test.fake_online_importer import OnlineImporter
from test.zip_objects import store_with_unzipped_cheats, cheats_folder_zip_desc, \
    cheats_folder_nes_file_path, \
    unzipped_summary_json_from_cheats_folder, \
    zipped_files_from_cheats_folder, cheats_folder_id, cheats_folder_sms_file_path, cheats_folder_folders, \
    cheats_folder_files, with_installed_cheats_folder_on_fs


class TestOnlineImporterWithZips(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = OnlineImporter()

    def download(self, db, store):
        self.sut.add_db(db, store)
        self.sut.download(False)
        return store

    def test_download_zipped_cheats_folder___on_empty_store_from_summary_and_contents_when_file_count_threshold_is_surpassed___installs_from_zip_content(self):
        self.sut.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents
        store = self.download_zipped_cheats_folder(empty_test_store(), from_zip_content=True)
        self.assertEqual(store_with_unzipped_cheats(url=False), store)

    def test_download_zipped_cheats_folder___on_empty_store_from_summary_and_contents_when_accumulated_mb_threshold_is_surpassed___installs_from_zip_content(self):
        self.sut.config['zip_accumulated_mb_threshold'] = 0  # This will cause to unzip the contents
        store = self.download_zipped_cheats_folder(empty_test_store(), from_zip_content=True)
        self.assertEqual(store_with_unzipped_cheats(url=False), store)

    def test_download_zipped_cheats_folder___on_empty_store_from_summary_but_no_contents_because_thresholds_are_not_surpassed___installs_from_url(self):
        self.assertEqual(store_with_unzipped_cheats(), self.download_zipped_cheats_folder(empty_test_store(), from_zip_content=False))

    def test_download_zipped_cheats_folder___with_already_downloaded_summary___restores_file_contained_in_summary(self):
        self.assertEqual(store_with_unzipped_cheats(), self.download_zipped_cheats_folder(store_with_unzipped_cheats(), from_zip_content=False))

    def test_download_zipped_cheats_folder___with_summary_containing_already_existing_files___updates_files_in_the_store_now_pointing_to_summary(self):
        self.assertEqual(store_with_unzipped_cheats(), self.download_zipped_cheats_folder(store_with_unzipped_cheats(zip_id=False, zips=False), from_zip_content=False))

    def test_download_zipped_contents___on_existing_store_with_zips___removes_old_zip_id_and_inserts_new_one(self):
        with_installed_cheats_folder_on_fs(self.sut.file_system)

        different_zip_id = 'a_different_id'
        different_folder = "Different"

        store = self.download(db_test_descr(zips={
            different_zip_id: zip_desc([different_folder], "./", different_folder, unzipped_json={
                "files": {file_a: zipped_file_a_descr(different_zip_id)},
                "files_count": 1,
                "folders": {different_folder: {"zip_id": different_zip_id}},
                "folders_count": 1,
            })
        }), store_with_unzipped_cheats())

        self.assertReports([file_a])
        self.assertEqual({
            "base_path": "/media/fat/",
            "files": {file_a: zipped_file_a_descr(different_zip_id, url=True)},
            "offline_databases_imported": [],
            "folders": {different_folder: {"zip_id": different_zip_id}},
            "zips": {different_zip_id: zip_desc([different_folder], "./", different_folder)}
        }, store)
        self.assertFalse(self.sut.file_system.is_file(cheats_folder_nes_file_path))
        self.assertFalse(self.sut.file_system.is_file(cheats_folder_sms_file_path))
        self.assertTrue(self.sut.file_system.is_file(file_a))

    def test_download_non_zipped_contents___with_file_already_on_store_with_zip_id___removes_zip_id_from_file_on_store(self):
        store = self.download(db_test_descr(
            folders=cheats_folder_folders(zip_id=False),
            files=cheats_folder_files(zip_id=False),
        ), store_with_unzipped_cheats())
        self.assertReports(list(cheats_folder_files()))
        self.assertEqual(store_with_unzipped_cheats(zip_id=False, zips=False, tags=False), store)

    def test_download_zip_summary___after_previous_summary_is_present_when_new_summary_is_found_with_no_file_changes___updates_summary_hash(self):
        with_installed_cheats_folder_on_fs(self.sut.file_system)

        previous_store = store_with_unzipped_cheats(url=False)
        expected_store = store_with_unzipped_cheats(url=False, summary_hash="something_new")

        actual_store = self.download(db_test_descr(zips={
            cheats_folder_id: cheats_folder_zip_desc(summary_hash="something_new", unzipped_json=unzipped_summary_json_from_cheats_folder())
        }), previous_store)

        self.assertReports([])
        self.assertEqual(expected_store, actual_store)

    def test_download_zip_summary_without_files___for_the_first_time___adds_zip_id_to_store(self):
        zip_descriptions = {cheats_folder_id: cheats_folder_zip_desc(unzipped_json=empty_zip_summary())}
        expected_store = store_test_descr(zips=zip_descriptions)
        actual_store = self.download(db_test_descr(zips=zip_descriptions), empty_test_store())
        self.assertEqual(expected_store, actual_store)

    def download_zipped_cheats_folder(self, input_store, from_zip_content):
        zipped_files = zipped_files_from_cheats_folder() if from_zip_content else None

        output_store = self.download(db_test_descr(zips={
            cheats_folder_id: cheats_folder_zip_desc(zipped_files=zipped_files, unzipped_json=unzipped_summary_json_from_cheats_folder())
        }), input_store)

        self.assertReports(list(cheats_folder_files()))

        return output_store

    def assertReports(self, installed, errors=None, needs_reboot=False):
        if errors is None:
            errors = []
        self.assertEqual(installed, self.sut.correctly_installed_files())
        self.assertEqual(errors, self.sut.files_that_failed())
        self.assertEqual(needs_reboot, self.sut.needs_reboot())
