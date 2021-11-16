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
from test.objects import store_with_unzipped_cheats_folder_nes_files, file_test_json_zip, cheats_folder_nes_file_path, db_test_descr, cheats_folder_nes_zip_desc
from test.objects import cheats_folder_nes_zip_id, cheats_folder_nes_file_hash, unzipped_json_with_cheats_folder_nes_file, cheats_folder_nes_file_size
from test.fake_offline_importer import OfflineImporter


class TestOfflineImporterWithZips(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = OfflineImporter()

    def test_apply_offline_db_with_zips___when_a_zipped_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(self):
        self.sut.file_system.test_data\
            .with_file(file_test_json_zip, {
                'hash': file_test_json_zip,
                'unzipped_json': db_test_descr(zips={
                    cheats_folder_nes_zip_id: cheats_folder_nes_zip_desc(unzipped_json=unzipped_json_with_cheats_folder_nes_file())
                }).to_dict()
            })\
            .with_file(cheats_folder_nes_file_path, {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size})

        store = self.apply_db_test_with_cheats_folder_nes_zip()

        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))
        self.assertEqual(store_with_unzipped_cheats_folder_nes_files(url=False, online_database_imported=[file_test_json_zip]), store)

    def apply_db_test_with_cheats_folder_nes_zip(self):
        store = empty_store()
        self.sut.add_db(db_test_descr(zips=cheats_folder_nes_zip_desc(), db_files=[file_test_json_zip]), store)
        self.sut.apply()
        return store
