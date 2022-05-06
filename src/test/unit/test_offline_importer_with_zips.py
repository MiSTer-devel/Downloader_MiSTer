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

from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects import file_test_json_zip, db_test_descr, empty_test_store
from test.zip_objects import cheats_folder_nes_file_hash, cheats_folder_nes_file_size, cheats_folder_nes_file_path, \
    cheats_folder_nes_folder_name, cheats_folder_zip_desc, store_with_unzipped_cheats, cheats_folder_id, \
    summary_json_from_cheats_folder, cheats_folder_sms_file_path, cheats_folder_sms_file_hash, \
    cheats_folder_sms_file_size, cheats_folder_sms_folder_name, cheats_folder_name
from test.fake_offline_importer import OfflineImporter


class TestOfflineImporterWithZips(unittest.TestCase):

    def test_apply_offline_db_with_zips___when_a_zipped_file_with_summary_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(self):
        self.assert_apply_offline_db_with_zips___when_a_zipped_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(is_summary_internal=False)

    def test_apply_offline_db_with_zips___when_a_zipped_file_with_internal_summary_is_present_with_correct_hash___adds_existing_a_file_to_the_store(self):
        self.assert_apply_offline_db_with_zips___when_a_zipped_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(is_summary_internal=True)

    def assert_apply_offline_db_with_zips___when_a_zipped_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(self, is_summary_internal):
        sut = OfflineImporter.from_implicit_inputs(ImporterImplicitInputs(
            files={
                file_test_json_zip: {
                    'hash': file_test_json_zip,
                    'unzipped_json': db_test_descr(zips={
                        cheats_folder_id: cheats_folder_zip_desc(summary=summary_json_from_cheats_folder(), is_summary_internal=is_summary_internal)
                    }).testable
                },
                cheats_folder_nes_file_path: {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size},
                cheats_folder_sms_file_path: {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size}
            },
            folders=[cheats_folder_nes_folder_name, cheats_folder_sms_folder_name, cheats_folder_name]
        ))
        store = self.apply_db_test_with_cheats_folder_nes_zip(sut)

        self.assertEqual(fs_data(
            files={
                cheats_folder_nes_file_path: {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size},
                cheats_folder_sms_file_path: {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size}
            },
            folders=[cheats_folder_nes_folder_name, cheats_folder_sms_folder_name, cheats_folder_name]
        ), sut.fs_data)

        self.assertEqual(store_with_unzipped_cheats(url=False, online_database_imported=[file_test_json_zip], is_summary_internal=is_summary_internal), store)

    def apply_db_test_with_cheats_folder_nes_zip(self, sut):
        store = empty_test_store()
        zips = {cheats_folder_id: cheats_folder_zip_desc()}
        sut.add_db(db_test_descr(zips=zips, db_files=[file_test_json_zip]), store)
        sut.apply()
        return store
