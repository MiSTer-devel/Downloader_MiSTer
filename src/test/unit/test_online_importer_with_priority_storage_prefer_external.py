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

from downloader.constants import MEDIA_FAT, MEDIA_USB0, MEDIA_USB1
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects import empty_test_store, file_nes_smb1, folder_games_nes, media_usb1, config_with, file_s32x_md, \
    media_usb0, file_neogeo_md, file_foo, file_s32x_md_descr, file_neogeo_md_descr, file_nes_contra, \
    db_id_external_drives_2, store_descr, db_id_external_drives_1, folder_games, media_usb2, folder_docs, \
    folder_docs_s32x, folder_docs_neogeo, media_usb3, zip_desc, file_nes_palette_a, \
    folder_games_nes_palettes
from test.unit.online_importer_with_priority_storage_test_base import fs_files_smb1_on_usb1, store_smb1_on_usb1, \
    fs_folders_games_on_usb1_usb2_and_fat, fs_folders_nes_on_fat_and_usb1, fs_folders_nes_on_fat_games_on_fat_usb1, \
    OnlineImporterWithPriorityStorageTestBase, fs_folders_nes_on_usb1_and_usb2, _store_files_foo, \
    _store_folders_nes, _store_files_contra, _store_files_neogeo_md, \
    _store_folders_docs_neogeo, _store_files_smb1, _store_files_s32x_md, _store_folders_docs_s32x, \
    fs_files_smb1_and_contra_on_usb0, fs_files_nes_palettes_on_fat, fs_folders_nes_palettes_on_fat, \
    fs_files_nes_palettes_on_usb1, fs_folders_nes_palettes_on_usb1
from test.zip_objects import zipped_nes_palettes_id, file_nes_palette_a_descr_zipped


class TestOnlineImporterWithPriorityStoragePreferExternal(OnlineImporterWithPriorityStorageTestBase):

    # @TODO: missing case
    # 1. setup with games and docs on fat
    # 2. copied all files to usb0
    # 3. run -> palettes get installed at fat instead of usb0
    # 4. problem was -> _import_zip_ids_from_store is used to recover summaries from the store, but there
    #                   paths are not stored with | symbol. Needed to change entries_in_zip to account for that.
    # This is not yet covered in a unit test, because externals are handled in a different layer
    # Need to do a system test at the very least

    def test_download_zipped_nes_palettes_db___on_empty_setup___downloads_gb_palettes_on_fat(self):
        store = empty_test_store()

        sut = self.download_zipped_nes_palettes_db(store, fs())

        expected_store = store_descr(
            files={file_nes_palette_a: file_nes_palette_a_descr_zipped()},
            folders={
                folder_games: {"zip_id": zipped_nes_palettes_id},
                folder_games_nes: {"zip_id": zipped_nes_palettes_id},
                folder_games_nes_palettes: {"zip_id": zipped_nes_palettes_id},
            },
            zips={zipped_nes_palettes_id: zip_desc(
                "Extracting Palettes",
                "|games/NES/",
            )}
        )

        self.assertEqual(expected_store, store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_fat(), folders=fs_folders_nes_palettes_on_fat()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a])

    def test_download_zipped_nes_palettes_db___on_empty_store_with_games_folder_on_usb1___downloads_gb_palettes_on_usb1(self):
        store = empty_test_store()

        sut = self.download_zipped_nes_palettes_db(store, fs(folders=[media_usb1(folder_games)]))

        expected_store = store_descr(
            files_usb1={file_nes_palette_a: file_nes_palette_a_descr_zipped()},
            folders_usb1={
                folder_games: {"zip_id": zipped_nes_palettes_id},
                folder_games_nes: {"zip_id": zipped_nes_palettes_id},
                folder_games_nes_palettes: {"zip_id": zipped_nes_palettes_id},
            },
            zips={zipped_nes_palettes_id: zip_desc(
                "Extracting Palettes",
                "|games/NES/",
            )}
        )

        self.assertEqual(expected_store, store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1(), folders=fs_folders_nes_palettes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a])

    def test_download_smb1_db___on_empty_store_with_nes_folder_on_usb1_and_usb2___downloads_smb1_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_usb2_and_fat___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_games_on_usb1_usb2_and_fat()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_games_on_usb1_usb2_and_fat() + [media_usb1(folder_games_nes)]), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_and_fat_but_nes_folder_on_fat___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_fat_games_on_fat_usb1()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_fat_and_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations(self):
        external_folders = [
            MEDIA_USB0,
            MEDIA_USB1,
            media_usb2(folder_games),
            media_usb3(folder_games),

            MEDIA_USB0,
            media_usb1(folder_docs),
            media_usb2(folder_docs),
            media_usb3(folder_docs),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(folders=external_folders))

        self.assertEqual({
            db_id_external_drives_1: store_descr(
                db_id=db_id_external_drives_1,
                files=_store_files_foo(),
                files_usb0={**_store_files_s32x_md(), **_store_files_smb1()}, folders_usb0={**_store_folders_docs_s32x(), **_store_folders_nes()},
            ),
            db_id_external_drives_2: store_descr(
                db_id=db_id_external_drives_2,
                files_usb0={**_store_files_neogeo_md(), **_store_files_contra()}, folders_usb0={**_store_folders_docs_neogeo(), **_store_folders_nes()},
            ),
        }, local_store_dbs)
        self.assertEqual(fs_data(
            files={
                **_store_files_foo(),
                media_usb0(file_neogeo_md): file_neogeo_md_descr(),
                media_usb0(file_s32x_md): file_s32x_md_descr(),
                **fs_files_smb1_and_contra_on_usb0(),
            },
            folders=[
                *external_folders,
                media_usb0(folder_games),
                media_usb0(folder_games_nes),
                media_usb0(folder_docs),
                media_usb0(folder_docs_neogeo),
                media_usb0(folder_docs_s32x),
            ]
        ), sut.fs_data)
        self.assertReports(sut, [file_foo, file_neogeo_md, file_s32x_md, file_nes_smb1, file_nes_contra])



def fs(files=None, folders=None, base_path=None):
    return ImporterImplicitInputs(
        config=config_with(storage_priority="prefer_external", base_system_path=MEDIA_FAT, zip_file_count_threshold=0),
        files=files,
        folders=folders,
        base_path=base_path
    )
