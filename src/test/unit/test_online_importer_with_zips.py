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
from downloader.other import empty_store
from test.objects import db_test_descr, cheats_folder_nes_folders, cheats_folder_nes_zip_desc, cheats_folder_nes_zip_id, cheats_folder_nes_file_path, store_with_unzipped_cheats_folder_nes_files, unzipped_json_with_cheats_folder_nes_file, cheats_folder_nes_file_hash, cheats_folder_nes_file_size
from test.objects import file_a, zipped_file_a_descr, zip_desc
from test.fakes import OnlineImporter


class TestOnlineImporterWithZips(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = OnlineImporter()

    def download_zipped_contents(self, db, store):
        self.sut.add_db(db, store)
        self.sut.download_dbs_contents(False)
        return store

    def test_download_zipped_contents___from_summary_and_contents___installs_zipped_file(self):
        self.sut.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents

        store = self.download_zipped_contents(db_test_descr(zips={
            cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(zipped_files={
                cheats_folder_nes_file_path: {
                    "hash": cheats_folder_nes_file_hash,
                    "size": cheats_folder_nes_file_size
                }
            }, unzipped_json=unzipped_json_with_cheats_folder_nes_file())
        }), empty_store())

        self.assertReports([cheats_folder_nes_file_path])
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(url=False), store)

    def test_download_zipped_contents___from_summary_but_standard_download___downloads_file_from_summary(self):
        store = self.download_zipped_contents(db_test_descr(zips={
            cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(unzipped_json=unzipped_json_with_cheats_folder_nes_file())
        }), empty_store())

        self.assertReports([cheats_folder_nes_file_path])
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(), store)

    def test_download_zipped_contents___on_existing_store_with_zips___removes_old_zip_id_and_inserts_new_one(self):
        self.sut.file_service.test_data\
            .with_folders(cheats_folder_nes_folders)\
            .with_file(cheats_folder_nes_file_path, {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size})

        different_zip_id = 'a_different_id'
        different_folder = "Different"

        store = self.download_zipped_contents(db_test_descr(zips={
            different_zip_id: zip_desc([different_folder], "./", different_folder, unzipped_json={
                "files": {file_a: zipped_file_a_descr(different_zip_id)},
                "files_count": 1,
                "folders": {different_folder: {"zip_id": different_zip_id}},
                "folders_count": 1,
            })
        }), store_with_unzipped_cheats_folder_nes_files())

        self.assertReports([file_a])
        self.assertEqual({
            "files": {file_a: zipped_file_a_descr(different_zip_id, url=True)},
            "offline_databases_imported": [],
            "folders": {different_folder: {"zip_id": different_zip_id}},
            "zips": {different_zip_id: zip_desc([different_folder], "./", different_folder)}
        }, store)
        self.assertFalse(self.sut.file_service.is_file(cheats_folder_nes_file_path))
        self.assertTrue(self.sut.file_service.is_file(file_a))

    def test_download_zipped_contents___with_already_downloaded_summary___restores_file_contained_in_summary(self):
        store = self.download_zipped_contents(db_test_descr(zips={
            cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(unzipped_json=unzipped_json_with_cheats_folder_nes_file())
        }), store_with_unzipped_cheats_folder_nes_files())

        self.assertReports([cheats_folder_nes_file_path])
        store["zips"][cheats_folder_nes_zip_id]["summary_file"].pop("unzipped_json")
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(), store)

    def test_download_zipped_contents___with_summary_containing_already_existing_files___updates_files_in_the_store_now_pointing_to_summary(self):
        store = self.download_zipped_contents(db_test_descr(zips={
            cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(unzipped_json=unzipped_json_with_cheats_folder_nes_file())
        }), store_with_unzipped_cheats_folder_nes_files(zip_id=False, zips=False))

        self.assertReports([cheats_folder_nes_file_path])
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(), store)

    def test_download_non_zipped_contents___with_file_already_on_store_with_zip_id___removes_zip_id_from_file_on_store(self):
        store = self.download_zipped_contents(db_test_descr(
            folders=cheats_folder_nes_folders,
            files={
                cheats_folder_nes_file_path: {
                    "hash": cheats_folder_nes_file_hash,
                    "size": cheats_folder_nes_file_size
                },
            }
        ), store_with_unzipped_cheats_folder_nes_files())
        self.assertReports([cheats_folder_nes_file_path])
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(zip_id=False, zips=False), store)

    def assertReports(self, installed, errors=None, needs_reboot=False):
        if errors is None:
            errors = []
        self.assertEqual(installed, self.sut.correctly_installed_files())
        self.assertEqual(errors, self.sut.files_that_failed())
        self.assertEqual(needs_reboot, self.sut.needs_reboot())
