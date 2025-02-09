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
from downloader.jobs.worker_context import DownloaderWorkerFailPolicy
from downloader.target_path_calculator import StoragePriorityError
from test.fake_file_system_factory import fs_data
from test.fake_online_importer import OnlineImporter
from test.objects import empty_test_store, file_nes_palette_a, file_nes_smb1, db_test, db_entity, file_nes_smb1_descr, files_smb1, folder_games, folder_games_nes, folder_games_nes_palettes\
    , media_fat, store_descr, zip_desc
from test.unit.online_importer.online_importer_with_priority_storage_test_base import OnlineImporterWithPriorityStorageTestBase
from test.zip_objects import file_nes_palette_a_descr_zipped,  zipped_nes_palettes_id


class TestOnlineImporterWithPriorityStorage(OnlineImporterWithPriorityStorageTestBase):
    def test_download_dbs_contents___with_wrong_db_including_system_and_external_paths_simultaneously___when_fault_tolerant___ignores_system_attribute_and_installs_files(self):
        sut = OnlineImporter(fail_policy=DownloaderWorkerFailPolicy.FAULT_TOLERANT)
        store = empty_test_store()

        sut.add_db(self._db_with_smb1_and_nes_palettes(), store).download(False)

        self.assertEqual(fs_data(files={
            **files_smb1(),
            file_nes_palette_a: file_nes_palette_a_descr_zipped(),
        }, folders={
            media_fat(folder_games_nes_palettes),
            media_fat(folder_games), media_fat(folder_games_nes)
        }), sut.fs_data)
        self.assertEqual(store_descr(
            zips={zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes)},
            files={
                file_nes_palette_a: {**file_nes_palette_a_descr_zipped(), 'path': 'system'},
                file_nes_smb1: {**file_nes_smb1_descr(), 'path': 'system'}
            },
            folders={
                folder_games: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
                folder_games_nes: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
                folder_games_nes_palettes: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
            }
        ), store)
        self.assertReports(sut, [file_nes_palette_a, file_nes_smb1])

    def test_download_dbs_contents___with_wrong_db_including_system_and_external_paths_simultaneously___when_fail_fast___ignores_system_attribute_and_installs_files(self):
        sut = OnlineImporter(fail_policy=DownloaderWorkerFailPolicy.FAIL_FAST)
        store = empty_test_store()

        with self.assertRaises(Exception) as context:
            sut.add_db(self._db_with_smb1_and_nes_palettes(), store).download(False)

        self.assertIsInstance(context.exception, StoragePriorityError)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [], save=False)

    def _db_with_smb1_and_nes_palettes(self):
        return db_entity(
            db_id=db_test,
            files={file_nes_smb1: {**file_nes_smb1_descr(), 'path': 'system'}},
            folders={folder_games: {'path': 'system'}, folder_games_nes: {'path': 'system'}},
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes,
                    summary={
                        "files": {file_nes_palette_a: {**file_nes_palette_a_descr_zipped(), 'path': 'system'}},
                        "folders": {
                            folder_games: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
                            folder_games_nes: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
                            folder_games_nes_palettes: {"zip_id": zipped_nes_palettes_id, 'path': 'system'},
                        }
                    }
                )
            }
        )
