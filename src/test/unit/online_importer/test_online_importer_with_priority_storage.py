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
from test.fake_file_system_factory import fs_data
from test.fake_online_importer import OnlineImporter
from test.objects import empty_test_store, file_nes_smb1, db_test, db_entity, file_nes_smb1_descr, folder_games, folder_games_nes
from test.unit.online_importer.online_importer_with_priority_storage_test_base import OnlineImporterWithPriorityStorageTestBase
from test.zip_objects import cheats_folder_zip_desc, summary_json_from_cheats_folder, cheats_folder_id


class TestOnlineImporterWithPriorityStorage(OnlineImporterWithPriorityStorageTestBase):
    def test_download_dbs_contents___with_wrong_db_including_system_and_external_paths_simultaneously___does_nothing_but_reports_errors(self):
        sut = OnlineImporter()
        store = empty_test_store()

        db = db_entity(
            db_id=db_test,
            files={file_nes_smb1: {**file_nes_smb1_descr(), 'path': 'system'}},
            folders={folder_games: {'path': 'system'}, folder_games_nes: {'path': 'system'}},
            zips={cheats_folder_id: {**cheats_folder_zip_desc(summary=summary_json_from_cheats_folder()), 'path': 'system'}}
        )

        sut.add_db(db, store).download(False)

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [],
                           errors=[file_nes_smb1],
                           failed_folders=[folder_games, folder_games_nes],
                           failed_zips=[cheats_folder_id],
                           save=False)

