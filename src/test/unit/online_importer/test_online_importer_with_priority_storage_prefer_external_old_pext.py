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
from downloader.constants import MEDIA_FAT, MEDIA_USB0, MEDIA_USB1, STORAGE_PRIORITY_PREFER_EXTERNAL
from objects import empty_test_store, store_descr, db_id_external_drives_1, db_id_external_drives_2
from test.fake_file_system_factory import fs_data
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.objects_old_pext import file_nes_smb1 as file_nes_smb1_old_pext, folder_games_nes as folder_games_nes_old_pext, \
    media_usb1 as media_usb1_old_pext, config_with as config_with_old_pext, \
    file_s32x_md as file_s32x_md_old_pext, media_usb0 as media_usb0_old_pext, \
    file_neogeo_md as file_neogeo_md_old_pext, file_foo as file_foo_old_pext, \
    file_s32x_md_descr as file_s32x_md_descr_old_pext, file_neogeo_md_descr as file_neogeo_md_descr_old_pext, \
    file_nes_contra as file_nes_contra_old_pext, db_id_external_drives_2 as db_id_external_drives_2_old_pext, \
    db_id_external_drives_1 as db_id_external_drives_1_old_pext, \
    folder_games as folder_games_old_pext, media_usb2 as media_usb2_old_pext, folder_docs as folder_docs_old_pext, \
    folder_docs_s32x as folder_docs_s32x_old_pext, folder_docs_neogeo as folder_docs_neogeo_old_pext, \
    media_usb3 as media_usb3_old_pext, file_nes_palette_a as file_nes_palette_a_old_pext, \
    clean_zip_test_fields as clean_zip_test_fields_old_pext
from test.unit.online_importer.online_importer_with_priority_storage_test_base_old_pext import \
    fs_files_smb1_on_usb1 as fs_files_smb1_on_usb1_old_pext, \
    fs_folders_games_on_usb1_usb2_and_fat as fs_folders_games_on_usb1_usb2_and_fat_old_pext, \
    fs_folders_nes_on_fat_and_usb1 as fs_folders_nes_on_fat_and_usb1_old_pext, \
    fs_folders_nes_on_fat_games_on_fat_usb1 as fs_folders_nes_on_fat_games_on_fat_usb1_old_pext, \
    OnlineImporterWithPriorityStorageTestBaseOldPext, \
    fs_folders_nes_on_usb1_and_usb2 as fs_folders_nes_on_usb1_and_usb2_old_pext, \
    _store_files_foo as _store_files_foo_old_pext, \
    _store_folders_nes as _store_folders_nes_old_pext, \
    _store_files_contra as _store_files_contra_old_pext, \
    _store_files_neogeo_md as _store_files_neogeo_md_old_pext, \
    _store_folders_docs_neogeo as _store_folders_docs_neogeo_old_pext, \
    _store_files_smb1 as _store_files_smb1_old_pext, \
    _store_files_s32x_md as _store_files_s32x_md_old_pext, \
    _store_folders_docs_s32x as _store_folders_docs_s32x_old_pext, \
    fs_files_smb1_and_contra_on_usb0 as fs_files_smb1_and_contra_on_usb0_old_pext, \
    fs_files_nes_palettes_on_fat as fs_files_nes_palettes_on_fat_old_pext, \
    fs_folders_nes_palettes_on_fat as fs_folders_nes_palettes_on_fat_old_pext, \
    fs_files_nes_palettes_on_usb1 as fs_files_nes_palettes_on_usb1_old_pext, \
    fs_folders_nes_palettes_on_usb1 as fs_folders_nes_palettes_on_usb1_old_pext, \
    fs_folders_nes_on_fat as fs_folders_nes_on_fat_old_pext, \
    fs_files_smb1_on_fat as fs_files_smb1_on_fat_old_pext, \
    fs_files_smb1_and_contra_on_usb2 as fs_files_smb1_and_contra_on_usb2_old_pext, \
    fs_folders_nes_on_usb1 as fs_folders_nes_on_usb1_old_pext
from unit.online_importer.online_importer_with_priority_storage_test_base import store_nes_zipped_palettes_on_usb1, \
    store_smb1_on_usb1, store_smb1, store_nes_zipped_palettes_on_fat, _store_files_foo, _store_files_s32x_md, \
    _store_files_smb1, _store_folders_docs_s32x, _store_folders_nes, _store_files_neogeo_md, _store_files_contra, \
    _store_folders_docs_neogeo


# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithPriorityStoragePreferExternalOldPext(OnlineImporterWithPriorityStorageTestBaseOldPext):

    def test_download_zipped_nes_palettes_db___on_empty_setup___downloads_gb_palettes_on_fat(self):
        store = empty_test_store()

        sut = self.download_zipped_nes_palettes_db(store, fs())

        self.assertEqual(store_nes_zipped_palettes_on_fat(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_fat_old_pext(), folders=fs_folders_nes_palettes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext])

    def test_download_zipped_nes_palettes_db___on_empty_store_with_games_folder_on_usb1___downloads_gb_palettes_on_usb1(self):
        store = empty_test_store()

        sut = self.download_zipped_nes_palettes_db(store, fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext])

    def test_download_palettes_db_from_local_store_pov___on_empty_store_with_empty_fs_usb1___installs_all_in_fs_usb1(self):
        store = empty_test_store()
        sut = self.download_zipped_nes_palettes_db(store, inputs=fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), clean_zip_test_fields_old_pext(store))
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext])

    def test_download_palettes_db_from_local_store_pov___on_store_with_palettes_on_usb1_but_empty_fs_usb1___installs_all_in_fs_usb1(self):
        store = store_nes_zipped_palettes_on_usb1()
        sut = self.download_zipped_nes_palettes_db(store, inputs=fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext], save=False)

    def test_download_palettes_db_from_local_store_pov___on_store_with_palettes_on_fat_but_empty_fs_usb1___installs_all_in_fs_usb1(self):
        store = store_nes_zipped_palettes_on_fat()
        sut = self.download_zipped_nes_palettes_db(store, inputs=fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext], save=True)

    def test_download_smb1_db_from_local_store_pov___on_store_with_smb1_on_fat_but_empty_fs_usb1___installs_all_in_fs_usb1(self):
        store = store_smb1()
        sut = self.download_smb1_db(store, inputs=fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext], save=True)

    def test_download_palettes_db_from_local_store_pov___on_store_with_palettes_on_fat_but_empty_fs_usb1___installs_all_in_fs_usb12(self):
        store = store_nes_zipped_palettes_on_fat()
        sut = self.download_zipped_nes_palettes_db(store, inputs=fs(folders=[media_usb1_old_pext(folder_games_old_pext)]))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext], save=True)

    def test_download_palettes_db_from_local_store_pov___on_store_with_palettes_on_usb1_and_fs___installs_nothing(self):
        store = store_nes_zipped_palettes_on_usb1()
        sut = self.download_zipped_nes_palettes_db(store, inputs=fs(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()))

        self.assertEqual(store_nes_zipped_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_smb1_db___on_empty_store_with_nes_folder_on_usb1_and_usb2___downloads_smb1_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_usb2_and_fat___downloads_smb1_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_games_on_usb1_usb2_and_fat_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_games_on_usb1_usb2_and_fat_old_pext() + [media_usb1_old_pext(folder_games_nes_old_pext)]), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_and_fat_but_nes_folder_on_fat___downloads_smb1_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_fat_games_on_fat_usb1_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___on_empty_store_with_just_games_nes_folder_on_fat___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_fat_old_pext()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations(self):
        external_folders = [
            MEDIA_USB0,
            MEDIA_USB1,
            media_usb2_old_pext(folder_games_old_pext),
            media_usb3_old_pext(folder_games_old_pext),

            MEDIA_USB0,
            media_usb1_old_pext(folder_docs_old_pext),
            media_usb2_old_pext(folder_docs_old_pext),
            media_usb3_old_pext(folder_docs_old_pext),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(folders=external_folders))

        self.assertEqual({
            db_id_external_drives_1_old_pext: store_descr(
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
                **_store_files_foo_old_pext(),
                media_usb0_old_pext(file_neogeo_md_old_pext): file_neogeo_md_descr_old_pext(),
                media_usb0_old_pext(file_s32x_md_old_pext): file_s32x_md_descr_old_pext(),
                **fs_files_smb1_and_contra_on_usb0_old_pext(),
            },
            folders=[
                *external_folders,
                media_usb0_old_pext(folder_games_old_pext),
                media_usb0_old_pext(folder_games_nes_old_pext),
                media_usb0_old_pext(folder_docs_old_pext),
                media_usb0_old_pext(folder_docs_neogeo_old_pext),
                media_usb0_old_pext(folder_docs_s32x_old_pext),
            ]
        ), sut.fs_data)
        self.assertReports(sut, [file_foo_old_pext, file_neogeo_md_old_pext, file_s32x_md_old_pext, file_nes_smb1_old_pext, file_nes_contra_old_pext])


    def better_test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations(self):
        external_folders = [
            MEDIA_USB0,
            MEDIA_USB1,
            media_usb2_old_pext(folder_games_old_pext),
            media_usb3_old_pext(folder_games_old_pext),

            MEDIA_USB0,
            media_usb1_old_pext(folder_docs_old_pext),
            media_usb2_old_pext(folder_docs_old_pext),
            media_usb3_old_pext(folder_docs_old_pext),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(folders=external_folders))

        self.assertEqual({
            db_id_external_drives_1_old_pext: store_descr(
                db_id=db_id_external_drives_1_old_pext,
                files=_store_files_foo_old_pext(),
                files_usb2={**_store_files_smb1_old_pext()}, folders_usb2={**_store_folders_nes_old_pext()},
                files_usb1={**_store_files_s32x_md_old_pext()}, folders_usb1={**_store_folders_docs_s32x_old_pext()},
            ),
            db_id_external_drives_2_old_pext: store_descr(
                db_id=db_id_external_drives_2_old_pext,
                files_usb2={**_store_files_contra_old_pext()}, folders_usb2={**_store_folders_nes_old_pext()},
                files_usb1={**_store_files_neogeo_md_old_pext()}, folders_usb1={**_store_folders_docs_neogeo_old_pext()},
            ),
        }, local_store_dbs)
        self.assertEqual(fs_data(
            files={
                **_store_files_foo_old_pext(),
                media_usb1_old_pext(file_neogeo_md_old_pext): file_neogeo_md_descr_old_pext(),
                media_usb1_old_pext(file_s32x_md_old_pext): file_s32x_md_descr_old_pext(),
                **fs_files_smb1_and_contra_on_usb2_old_pext(),
            },
            folders=[
                *external_folders,
                media_usb2_old_pext(folder_games_old_pext),
                media_usb2_old_pext(folder_games_nes_old_pext),
                media_usb1_old_pext(folder_docs_old_pext),
                media_usb1_old_pext(folder_docs_neogeo_old_pext),
                media_usb1_old_pext(folder_docs_s32x_old_pext),
            ]
        ), sut.fs_data)
        self.assertReports(sut, [file_foo_old_pext, file_neogeo_md_old_pext, file_s32x_md_old_pext, file_nes_smb1_old_pext, file_nes_contra_old_pext])


    def better_test_download_external_drives_1_and_2___on_store_and_fs____installs_at_expected_locations(self):
        initial_local_store_dbs = {
            db_id_external_drives_1_old_pext: store_descr(
                db_id=db_id_external_drives_1_old_pext,
                files=_store_files_foo_old_pext(),
                files_usb0={**_store_files_s32x_md_old_pext(), **_store_files_smb1_old_pext()}, folders_usb0={**_store_folders_docs_s32x_old_pext(), **_store_folders_nes_old_pext()},
            ),
            db_id_external_drives_2_old_pext: store_descr(
                db_id=db_id_external_drives_2_old_pext,
                files_usb0={**_store_files_neogeo_md_old_pext(), **_store_files_contra_old_pext()}, folders_usb0={**_store_folders_docs_neogeo_old_pext(), **_store_folders_nes_old_pext()},
            ),
        }

        external_folders = [
            MEDIA_USB0,
            MEDIA_USB1,
            media_usb2_old_pext(folder_games_old_pext), media_usb2_old_pext(folder_games_nes_old_pext),
            media_usb3_old_pext(folder_games_old_pext),

            media_usb0_old_pext(folder_docs_old_pext),
            media_usb1_old_pext(folder_docs_old_pext), media_usb2_old_pext(folder_docs_neogeo_old_pext), media_usb2_old_pext(folder_docs_s32x_old_pext),
            media_usb2_old_pext(folder_docs_old_pext),
            media_usb3_old_pext(folder_docs_old_pext),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(folders=external_folders), store=initial_local_store_dbs)

        # self.assertEqual({
        #     db_id_external_drives_1_old_pext: store_descr(
        #         db_id=db_id_external_drives_1_old_pext,
        #         files=_store_files_foo(),
        #         files_usb2={**_store_files_smb1()}, folders_usb2={**_store_folders_nes()},
        #         files_usb1={**_store_files_s32x_md()}, folders_usb1={**_store_folders_docs_s32x()},
        #     ),
        #     db_id_external_drives_2_old_pext: store_descr(
        #         db_id=db_id_external_drives_2_old_pext,
        #         files_usb2={**_store_files_contra()}, folders_usb2={**_store_folders_nes()},
        #         files_usb1={**_store_files_neogeo_md()}, folders_usb1={**_store_folders_docs_neogeo()},
        #     ),
        # }, local_store_dbs)
        self.assertEqual(fs_data(
            files={
                **_store_files_foo_old_pext(),
                media_usb0_old_pext(file_neogeo_md_old_pext): file_neogeo_md_descr_old_pext(),
                media_usb0_old_pext(file_s32x_md_old_pext): file_s32x_md_descr_old_pext(),
                **fs_files_smb1_and_contra_on_usb0_old_pext(),
            },
            folders=[
                *external_folders,
                media_usb0_old_pext(folder_games_old_pext),
                media_usb0_old_pext(folder_games_nes_old_pext),
                media_usb0_old_pext(folder_docs_old_pext),
                media_usb0_old_pext(folder_docs_neogeo_old_pext),
                media_usb0_old_pext(folder_docs_s32x_old_pext),
            ]
        ), sut.fs_data)
        self.assertReports(sut, [file_foo_old_pext, file_neogeo_md_old_pext, file_s32x_md_old_pext, file_nes_smb1_old_pext, file_nes_contra_old_pext], save=False)

def fs(files=None, folders=None, base_path=None):
    return ImporterImplicitInputs(
        config=config_with_old_pext(storage_priority=STORAGE_PRIORITY_PREFER_EXTERNAL, base_system_path=MEDIA_FAT, zip_file_count_threshold=0),
        files=files,
        folders=folders,
        base_path=base_path
    )
