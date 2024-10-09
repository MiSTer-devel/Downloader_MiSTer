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

from downloader.constants import FILE_PDFViewer, MEDIA_FAT
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects import empty_test_store, store_descr, media_fat, file_nes_smb1, folder_games, \
    folder_games_nes, media_usb1, media_usb2, config_with, file_nes_contra, file_nes_palette_a, file_nes_manual, \
    folder_docs, db_id_external_drives_1, db_id_external_drives_2, file_neogeo_md, file_neogeo_md_descr, file_s32x_md, \
    file_s32x_md_descr, media_usb0, folder_docs_neogeo, folder_docs_s32x, file_foo, empty_store, folder_a, folder_games_md, files_a, \
    store_test_with_file_a_descr, file_a, file_md_sonic, db_test_with_file_a, db_smb1, db_sonic
from test.unit.online_importer.online_importer_with_priority_storage_test_base import fs_folders_nes_on_usb1_and_usb2, \
    fs_files_smb1_on_usb1, store_smb1_on_usb1, fs_folders_nes_on_usb2, store_smb1_on_usb2, fs_files_smb1_on_usb2, \
    store_smb1_on_usb1_and_usb2, fs_files_smb1_on_usb1_and_usb2, fs_folders_games_on_usb1_and_usb2, \
    store_nes_folder_on_usb1, fs_folders_nes_on_usb1, fs_folders_games_on_usb1_usb2_and_fat, store_smb1, \
    fs_files_smb1_on_fat, fs_folders_nes_on_fat, fs_files_smb1_on_fat_and_usb1, fs_folders_nes_on_fat_and_usb1, \
    store_smb1_on_fat_and_usb1, fs_folders_nes_on_fat_games_on_fat_usb1, store_smb1_and_contra, \
    fs_files_smb1_and_contra_on_fat, fs_files_smb1_and_contra_on_fat_contra_on_usb1_too, \
    store_smb1_and_contra_on_fat_and_usb1, fs_files_smb1_and_contra_on_fat_and_usb1, \
    fs_files_smb1_on_fat_contra_on_usb1, store_smb1_on_fat_and_smb1_and_contra_on_usb1, \
    fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too, store_smb1_and_nes_palettes, \
    fs_files_smb1_and_nes_palettes_on_fat, fs_folders_nes_palettes_on_fat, store_smb1_and_nes_palettes_on_usb1, \
    fs_files_smb1_and_nes_palettes_on_usb1, fs_folders_nes_palettes_on_usb1, store_smb1_on_usb1_and_nes_manual_on_usb2, \
    fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2, fs_files_smb1_on_usb1_and_nes_manual_on_usb2, \
    fs_files_smb1_and_contra_on_usb2, delme_drive, store_smb1_on_delme, fs_files_smb1_on_delme, \
    fs_folders_nes_on_delme, hidden_drive, store_pdfviewer_on_base_system_path_hidden, fs_folders_pdfviewers_on_hidden, \
    fs_files_pdfviewers_on_hidden, _store_files_foo, _store_files_s32x_md, _store_files_smb1, _store_folders_nes, \
    _store_folders_docs_s32x, _store_folders_docs_neogeo, _store_files_neogeo_md, _store_files_contra, \
    OnlineImporterWithPriorityStorageTestBase, store_nes_folder, store_just_nes_palettes_on_usb1, fs_files_nes_palettes_on_usb1, \
    store_smb1_on_fat, fs_files_sonic_on_usb1, store_sonic_on_usb1


class TestOnlineImporterWithPriorityStoragePreferSD(OnlineImporterWithPriorityStorageTestBase):
    def test_download_smb1_db___on_empty_store_with_nes_folder_on_usb1_and_usb2___downloads_smb1_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___after_previous_run___downloads_nothing(self):
        store = store_smb1_on_usb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_empty_db___after_previous_run___removes_files_from_usb1_but_keeps_usb1_and_usb2_folders(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___after_previous_run_and_manually_deleting_usb1_folders___downloads_smb1_on_usb2(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb2()))

        self.assertEqual(store_smb1_on_usb2(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb2(), folders=fs_folders_nes_on_usb2()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___after_copying_files_to_usb1___updates_the_store_with_usb1_and_usb2(self):
        store = store_smb1_on_usb2()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1_and_usb2(), folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(store_smb1_on_usb1_and_usb2(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_and_usb2(), folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___after_removing_nes_folders_on_external_drives_with_store_referencing_missing_files___lets_the_store_with_just_games_folders(self):
        store = store_smb1_on_usb1_and_usb2()

        sut = self.download_empty_db(store, fs(folders=fs_folders_games_on_usb1_and_usb2()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_games_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_folders_installed_on_usb1___keeps_same_store_and_fs(self):
        store = store_nes_folder_on_usb1()

        sut = self.download_empty_db(store, fs(folders=fs_folders_nes_on_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_smb1_on_usb1_and_usb2___removes_smb1_but_keeps_nes_folders(self):
        store = store_smb1_on_usb1_and_usb2()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1_and_usb2(), folders=fs_folders_nes_on_usb1_and_usb2()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_and_usb2()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_usb2_and_fat___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_games_on_usb1_usb2_and_fat()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat(), folders=fs_folders_games_on_usb1_usb2_and_fat() + [media_fat(folder_games_nes)]), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___on_empty_store_and_nothing_on_fs___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs())

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat(), folders=fs_folders_nes_on_fat()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___after_previous_run___does_nothing(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_fat(), folders=fs_folders_nes_on_fat()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat(), folders=fs_folders_nes_on_fat()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_smb1_db___after_copying_smb1_to_usb1___just_updates_store(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(store_smb1_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___after_copied_smb1_to_usb1___removes_everything_except_games_and_nes_folder_on_usb1(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___after_moving_smb1_to_usb1___just_updates_store(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___after_moved_smb1_to_usb1___just_keeps_nes_folder_on_usb1(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1(), folders=fs_folders_nes_on_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_and_fat_but_nes_folder_on_fat___downloads_smb1_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_fat_games_on_fat_usb1()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat(), folders=fs_folders_nes_on_fat_games_on_fat_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_smb1_db___on_empty_setup_and_base_path_delme___installs_smb1_on_delme(self):
        store = empty_store(base_path=delme_drive)

        sut = self.download_smb1_db(store, fs(base_path=delme_drive))

        self.assertEqual(store_smb1_on_delme(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_delme(), folders=fs_folders_nes_on_delme()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_empty_db___after_smb1_was_installed_on_base_path_delme___removes_smb1(self):
        store = store_smb1_on_delme()

        sut = self.download_empty_db(store, fs(base_path=delme_drive, files=fs_files_smb1_on_delme(), folders=fs_folders_nes_on_delme()))

        self.assertEqual(empty_store(base_path=delme_drive), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_smb1_installed_on_delme_and_fat_and_config_with_base_path_delme___removes_smb1_only_on_delme(self):
        store = store_smb1_on_delme()

        sut = self.download_empty_db(store, fs(base_path=delme_drive, folders=[*fs_folders_nes_on_delme(), *fs_folders_nes_on_fat()], files={**fs_files_smb1_on_delme(), **fs_files_smb1_on_fat()}))

        self.assertEqual(empty_store(delme_drive), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_fat(), files=fs_files_smb1_on_fat()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_nes_folder_installed_on_delme_and_fat_and_config_with_base_path_delme___removes_nes_folder_only_on_delme(self):
        store = store_nes_folder()

        sut = self.download_empty_db(store, fs(base_path=delme_drive, folders=[*fs_folders_nes_on_delme(), *fs_folders_nes_on_fat()]))

        self.assertEqual(empty_store(delme_drive), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_fat()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_pdfviewer_db___on_empty_setup_and_base_system_path_hidden___installs_pdfviewer_on_hidden(self):
        store = empty_test_store()

        sut = self.download_pdfviewer_db(store, fs(config=config_with(base_system_path=hidden_drive)))

        self.assertEqual(store_pdfviewer_on_base_system_path_hidden(), store)
        self.assertEqual(fs_data(folders=fs_folders_pdfviewers_on_hidden(), files=fs_files_pdfviewers_on_hidden()), sut.fs_data)
        self.assertReports(sut, [FILE_PDFViewer])

    def test_download_empty_db___after_pdfviewer_was_installed_on_base_system_path_hidden___removes_pdfviewer_and_linux_folder(self):
        store = store_pdfviewer_on_base_system_path_hidden()

        sut = self.download_empty_db(store, fs(config=config_with(base_system_path=hidden_drive), folders=fs_folders_pdfviewers_on_hidden(), files=fs_files_pdfviewers_on_hidden()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_contra___on_empty_store_and_nothing_on_fs___downloads_smb1_and_contra_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_and_contra(store, fs())

        self.assertEqual(store_smb1_and_contra(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat(), folders=fs_folders_nes_on_fat()), sut.fs_data)
        self.assertReports(sut, [file_nes_contra, file_nes_smb1])

    def test_download_smb1_and_contra___after_previous_run___does_nothing(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_and_contra_on_fat(), folders=fs_folders_nes_on_fat()))

        self.assertEqual(store_smb1_and_contra(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat(), folders=fs_folders_nes_on_fat()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_smb1_and_contra___after_copying_contra_to_usb1___downloads_smb_to_usb1(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_and_contra_on_fat_contra_on_usb1_too(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(store_smb1_and_contra_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_empty_db___after_copied_contra_to_usb1___removes_everything_except_nes_folder_on_usb1(self):
        store = store_smb1_and_contra_on_fat_and_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_contra_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_contra___after_moving_contra_to_usb1___downloads_smb_to_usb1(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_on_fat_contra_on_usb1(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(store_smb1_on_fat_and_smb1_and_contra_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too(), folders=fs_folders_nes_on_fat_and_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1])

    def test_download_empty_db___after_moved_contra_to_usb1___removes_everything_except_games_and_nes_folder_on_usb1(self):
        store = store_smb1_on_fat_and_smb1_and_contra_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_nes_palettes___on_empty_setup___installs_smb1_and_nes_palettes_on_fat(self):
        store = empty_test_store()

        sut = self.download_smb1_and_palettes(store, fs())

        self.assertEqual(store_smb1_and_nes_palettes(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_nes_palettes_on_fat(), folders=fs_folders_nes_palettes_on_fat()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a, file_nes_smb1])

    def test_download_empty_db___after_installing_smb1_and_nes_on_fat___removes_everything(self):
        store = store_smb1_and_nes_palettes()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_fat(), folders=fs_folders_nes_palettes_on_fat()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_nes_palettes___on_empty_store_with_nes_folder_on_usb1___installs_smb1_and_nes_palettes_on_usb1(self):
        store = empty_test_store()

        sut = self.download_smb1_and_palettes(store, fs(folders=fs_folders_nes_on_usb1()))

        self.assertEqual(store_smb1_and_nes_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_nes_palettes_on_usb1(), folders=fs_folders_nes_palettes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a, file_nes_smb1])

    def test_download_empty_db___after_installing_smb1_and_nes_on_usb1___removes_everything_except_nes_folder_on_usb1(self):
        store = store_smb1_and_nes_palettes_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_usb1(), folders=fs_folders_nes_palettes_on_usb1()))

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_in_db_test_and_nes_manual_in_db_demo___on_empty_stores_with_games_nes_folder_on_usb1_and_docs_nes_folder_on_usb2___installs_smb1_on_usb1_and_nes_manual_on_usb2(self):
        sut, local_store_dbs = self.download_smb1_in_db_test_and_nes_manual_in_db_demo(fs(folders=fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2()))

        self.assertEqual(store_smb1_on_usb1_and_nes_manual_on_usb2(), local_store_dbs)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_and_nes_manual_on_usb2(), folders=fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1, file_nes_manual])

    def test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations(self):
        external_folders = [
            media_usb0(folder_games),
            media_usb2(folder_games), media_usb2(folder_games_nes),

            media_usb0(folder_docs), media_usb0(folder_docs_neogeo),
            media_usb1(folder_docs), media_usb1(folder_docs_s32x),
            media_usb2(folder_docs),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(config=config_with(base_system_path=MEDIA_FAT), folders=external_folders))

        self.assertEqual({
            db_id_external_drives_1: store_descr(
                db_id=db_id_external_drives_1,
                files=_store_files_foo(),
                files_usb1=_store_files_s32x_md(), folders_usb1=_store_folders_docs_s32x(),
                files_usb2=_store_files_smb1(), folders_usb2=_store_folders_nes(),
            ),
            db_id_external_drives_2: store_descr(
                db_id=db_id_external_drives_2,
                files_usb0=_store_files_neogeo_md(), folders_usb0=_store_folders_docs_neogeo(),
                files_usb2=_store_files_contra(), folders_usb2=_store_folders_nes(),
            ),
        }, local_store_dbs)
        self.assertEqual(fs_data(
            files={
                **_store_files_foo(),
                media_usb0(file_neogeo_md): file_neogeo_md_descr(),
                media_usb1(file_s32x_md): file_s32x_md_descr(),
                **fs_files_smb1_and_contra_on_usb2(),
            },
            folders=external_folders
        ), sut.fs_data)
        self.assertReports(sut, [file_foo, file_neogeo_md, file_s32x_md, file_nes_smb1, file_nes_contra])

    def test_download_just_nes_palette_file_db___after_installing_smb1_and_nes_palettes_on_usb1___removes_everything_except_nes_palettes_on_usb1(self):
        store = store_smb1_and_nes_palettes_on_usb1()

        sut = self.download_just_nes_palette_file_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_usb1(), folders=fs_folders_nes_palettes_on_usb1()))

        self.assertEqual(store_just_nes_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1(), folders=fs_folders_nes_palettes_on_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_just_smb1_file_db___with_smb1_and_contra_on_fat_and_usb1___removes_contra_and_keeps_smb1_on_fat_and_usb1_with_its_folders(self):
        store = store_smb1_and_contra_on_fat_and_usb1()

        sut = self.download_just_smb1_file_db(store, fs(files=fs_files_smb1_and_contra_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()))

        self.assertEqual(store_smb1_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_and_usb1(), folders=fs_folders_nes_on_fat_and_usb1()), sut.fs_data)
        self.assertReports(sut, [])

    def test_delme_download_three_dbs_with_sd_priority_files___on_empty_system_with_some_folders____installs_all_in_fat_except_md(self):
        sut, stores = self.download_three_dbs_with_sd_priority_files(
            with_fs=fs(
                folders=[folder_a, folder_games, folder_games_nes, media_usb1(folder_games), media_usb1(folder_games_md)]
            )
        )
        self.assertSystem({
            "fs": fs_data(files=installed_three_dbs_fs_files(), folders=installed_three_dbs_fs_folders()),
            "stores": installed_three_dbs_store(),
            "ok": [file_a, file_nes_smb1, file_md_sonic],
        }, sut, stores)

    def test_delme_download_three_dbs_with_sd_priority_files___on_second_run____doesnt_save_anything(self):
        sut, stores = self.download_three_dbs_with_sd_priority_files(
            input_stores=installed_three_dbs_store(),
            with_fs=fs(files=installed_three_dbs_fs_files(), folders=installed_three_dbs_fs_folders())
        )
        self.assertSystem({
            "fs": fs_data(files=installed_three_dbs_fs_files(), folders=installed_three_dbs_fs_folders()),
            "stores": installed_three_dbs_store(),
            "save": False,
        }, sut, stores)

    def download_three_dbs_with_sd_priority_files(self, input_stores=None, with_fs=None):
        return self._download_databases(
            fs(folders=[media_usb1(folder_games), media_fat(folder_games)]) if with_fs is None else with_fs,
            [db_test_with_file_a(db_id='1'), db_smb1(db_id='2'), db_sonic(db_id='3')],
            input_stores=input_stores
        )


def fs(files=None, folders=None, base_path=None, config=None):
    return ImporterImplicitInputs(files=files, folders=folders, base_path=base_path, config=config)


def installed_three_dbs_fs_files(): return {**files_a(), **fs_files_smb1_on_fat(), **fs_files_sonic_on_usb1()}
def installed_three_dbs_fs_folders(): return [folder_a, folder_games, folder_games_nes, media_usb1(folder_games), media_usb1(folder_games_md)]
def installed_three_dbs_store(): return [store_test_with_file_a_descr(), store_smb1_on_fat(), store_sonic_on_usb1()]

