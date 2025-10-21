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

from downloader.constants import FILE_PDFViewer, MEDIA_FAT, K_BASE_PATH
from objects import empty_store, store_descr, store_test_with_file_a_descr, db_id_external_drives_1, \
    db_id_external_drives_2
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects_old_pext import empty_test_store as empty_test_store_old_pext, \
    media_fat as media_fat_old_pext, file_nes_smb1 as file_nes_smb1_old_pext, \
    folder_games as folder_games_old_pext, folder_games_nes as folder_games_nes_old_pext, \
    media_usb1 as media_usb1_old_pext, media_usb2 as media_usb2_old_pext, config_with as config_with_old_pext, \
    file_nes_contra as file_nes_contra_old_pext, file_nes_palette_a as file_nes_palette_a_old_pext, \
    file_nes_manual as file_nes_manual_old_pext, folder_docs as folder_docs_old_pext, \
    file_neogeo_md as file_neogeo_md_old_pext, file_neogeo_md_descr as file_neogeo_md_descr_old_pext, \
    file_s32x_md as file_s32x_md_old_pext, file_s32x_md_descr as file_s32x_md_descr_old_pext, \
    media_usb0 as media_usb0_old_pext, folder_docs_neogeo as folder_docs_neogeo_old_pext, \
    folder_docs_s32x as folder_docs_s32x_old_pext, file_foo as file_foo_old_pext, \
    empty_store as empty_store_old_pext, folder_a as folder_a_old_pext, \
    folder_games_md as folder_games_md_old_pext, files_a as files_a_old_pext, \
   file_a as file_a_old_pext, file_md_sonic as file_md_sonic_old_pext, db_test_with_file_a as db_test_with_file_a_old_pext, \
    db_smb1 as db_smb1_old_pext, db_sonic as db_sonic_old_pext
from test.unit.online_importer.online_importer_with_priority_storage_test_base_old_pext import \
    fs_folders_nes_on_usb1_and_usb2 as fs_folders_nes_on_usb1_and_usb2_old_pext, \
    fs_files_smb1_on_usb1 as fs_files_smb1_on_usb1_old_pext, \
    fs_folders_nes_on_usb2 as fs_folders_nes_on_usb2_old_pext, \
    fs_files_smb1_on_usb2 as fs_files_smb1_on_usb2_old_pext, \
    fs_files_smb1_on_usb1_and_usb2 as fs_files_smb1_on_usb1_and_usb2_old_pext, \
    fs_folders_games_on_usb1_and_usb2 as fs_folders_games_on_usb1_and_usb2_old_pext, \
    fs_folders_nes_on_usb1 as fs_folders_nes_on_usb1_old_pext, \
    fs_folders_games_on_usb1_usb2_and_fat as fs_folders_games_on_usb1_usb2_and_fat_old_pext, \
    fs_files_smb1_on_fat as fs_files_smb1_on_fat_old_pext, \
    fs_folders_nes_on_fat as fs_folders_nes_on_fat_old_pext, \
    fs_files_smb1_on_fat_and_usb1 as fs_files_smb1_on_fat_and_usb1_old_pext, \
    fs_folders_nes_on_fat_and_usb1 as fs_folders_nes_on_fat_and_usb1_old_pext, \
    fs_folders_nes_on_fat_games_on_fat_usb1 as fs_folders_nes_on_fat_games_on_fat_usb1_old_pext, \
    fs_files_smb1_and_contra_on_fat as fs_files_smb1_and_contra_on_fat_old_pext, \
    fs_files_smb1_and_contra_on_fat_contra_on_usb1_too as fs_files_smb1_and_contra_on_fat_contra_on_usb1_too_old_pext, \
    fs_files_smb1_and_contra_on_fat_and_usb1 as fs_files_smb1_and_contra_on_fat_and_usb1_old_pext, \
    fs_files_smb1_on_fat_contra_on_usb1 as fs_files_smb1_on_fat_contra_on_usb1_old_pext, \
    fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too as fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too_old_pext, \
    fs_files_smb1_and_nes_palettes_on_fat as fs_files_smb1_and_nes_palettes_on_fat_old_pext, \
    fs_folders_nes_palettes_on_fat as fs_folders_nes_palettes_on_fat_old_pext, \
    fs_files_smb1_and_nes_palettes_on_usb1 as fs_files_smb1_and_nes_palettes_on_usb1_old_pext, \
    fs_folders_nes_palettes_on_usb1 as fs_folders_nes_palettes_on_usb1_old_pext, \
    fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2 as fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2_old_pext, \
    fs_files_smb1_on_usb1_and_nes_manual_on_usb2 as fs_files_smb1_on_usb1_and_nes_manual_on_usb2_old_pext, \
    fs_files_smb1_and_contra_on_usb2 as fs_files_smb1_and_contra_on_usb2_old_pext, \
    delme_drive as delme_drive_old_pext, \
    fs_files_smb1_on_delme as fs_files_smb1_on_delme_old_pext, fs_folders_nes_on_delme as fs_folders_nes_on_delme_old_pext, \
    hidden_drive as hidden_drive_old_pext, \
    fs_folders_pdfviewers_on_hidden as fs_folders_pdfviewers_on_hidden_old_pext, \
    fs_files_pdfviewers_on_hidden as fs_files_pdfviewers_on_hidden_old_pext, \
    _store_files_foo as _store_files_foo_old_pext, \
    OnlineImporterWithPriorityStorageTestBaseOldPext as OnlineImporterWithPriorityStorageTestBaseOldPext, \
    fs_files_nes_palettes_on_usb1 as fs_files_nes_palettes_on_usb1_old_pext, \
    fs_files_sonic_on_usb1 as fs_files_sonic_on_usb1_old_pext
from unit.online_importer.online_importer_with_priority_storage_test_base import store_smb1_on_usb1, \
    store_nes_folder_on_usb1, store_smb1_on_usb2, store_smb1_on_usb1_and_usb2, store_nes_folder_on_usb1_and_usb2, \
    store_smb1, store_smb1_on_fat_and_usb1, store_smb1_on_delme, store_pdfviewer_on_base_system_path_hidden, \
    store_smb1_and_contra, store_smb1_and_contra_on_fat_and_usb1, store_smb1_on_fat_and_smb1_and_contra_on_usb1, \
    store_smb1_and_nes_palettes, store_smb1_and_nes_palettes_on_usb1, store_smb1_on_usb1_and_nes_manual_on_usb2, \
    store_just_nes_palettes_on_usb1, store_smb1_on_fat, store_sonic_on_usb1, store_nes_folder, _store_files_foo, \
    _store_files_s32x_md, _store_files_smb1, _store_folders_docs_s32x, _store_folders_nes, _store_files_contra, \
    _store_folders_docs_neogeo, _store_files_neogeo_md


# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithPriorityStoragePreferSDOldPext(OnlineImporterWithPriorityStorageTestBaseOldPext):
    def test_download_smb1_db___on_empty_store_with_nes_folder_on_usb1_and_usb2___downloads_smb1_on_usb1(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___after_previous_run___downloads_nothing(self):
        store = store_smb1_on_usb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_empty_db___after_previous_run___removes_files_from_usb1_but_keeps_usb1_and_usb2_folders(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___after_previous_run_and_manually_deleting_usb1_folders___downloads_smb1_on_usb2(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb2(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb2_old_pext(), folders=fs_folders_nes_on_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___after_copying_files_to_usb1___updates_the_store_with_validated_usb1_and_keeps_usb2(self):
        store = store_smb1_on_usb2()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1_and_usb2_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb1_and_usb2(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_and_usb2_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, downloaded=[], validated=[file_nes_smb1_old_pext])

    def test_download_empty_db___after_removing_nes_folders_on_external_drives_with_store_referencing_missing_files___lets_the_store_with_just_games_folders(self):
        store = store_smb1_on_usb1_and_usb2()

        sut = self.download_empty_db(store, fs(folders=fs_folders_games_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1_and_usb2(), store)
        self.assertEqual(fs_data(folders=fs_folders_games_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_folders_installed_on_usb1___keeps_same_store_and_fs(self):
        store = store_nes_folder_on_usb1()

        sut = self.download_empty_db(store, fs(folders=fs_folders_nes_on_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_empty_db___with_smb1_on_usb1_and_usb2___removes_smb1_but_keeps_nes_folders(self):
        store = store_smb1_on_usb1_and_usb2()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1_and_usb2_old_pext(), folders=fs_folders_nes_on_usb1_and_usb2_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1_and_usb2(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_and_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_usb2_and_fat___downloads_smb1_on_fat(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_games_on_usb1_usb2_and_fat_old_pext()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_games_on_usb1_usb2_and_fat_old_pext() + [media_fat_old_pext(folder_games_nes_old_pext)]), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___on_empty_store_and_nothing_on_fs___downloads_smb1_on_fat(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_db(store, fs())

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___after_previous_run___does_nothing(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_smb1_db___after_copying_smb1_to_usb1___just_updates_store_and_validates_smb1_on_usb1(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_smb1_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, downloaded=[], validated=[file_nes_smb1_old_pext])

    def test_download_empty_db___after_copied_smb1_to_usb1___removes_everything_except_games_and_nes_folder_on_usb1(self):
        store = store_smb1_on_fat_and_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_usb1_store_after_copying_all_to_fat___removes_whole_store_except_games_in_case_user_removes_subfolder_but_removes_usb1_file_and_keeps_the_rest_of_fs(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___after_moving_smb1_to_usb1___updates_store_and_validates_smb_on_usb1(self):
        store = store_smb1()

        sut = self.download_smb1_db(store, fs(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_old_pext()))

        self.assertEqual(store_smb1_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, downloaded=[], validated=[file_nes_smb1_old_pext])

    def test_download_empty_db___after_moved_smb1_to_usb1___just_keeps_nes_folder_on_usb1(self):
        store = store_smb1_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_on_usb1_old_pext(), folders=fs_folders_nes_on_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_db___on_empty_store_with_games_folder_on_usb1_and_fat_but_nes_folder_on_fat___downloads_smb1_on_fat(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_db(store, fs(folders=fs_folders_nes_on_fat_games_on_fat_usb1_old_pext()))

        self.assertEqual(store_smb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_old_pext(), folders=fs_folders_nes_on_fat_games_on_fat_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_smb1_db___on_empty_setup_and_base_path_delme___installs_smb1_on_delme(self):
        store = empty_store_old_pext(base_path=delme_drive_old_pext)

        sut = self.download_smb1_db(store, fs(base_path=delme_drive_old_pext))

        self.assertEqual(store_smb1_on_delme(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_delme_old_pext(), folders=fs_folders_nes_on_delme_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext])

    def test_download_empty_db___after_smb1_was_installed_on_base_path_delme___removes_smb1(self):
        store = store_smb1_on_delme()

        sut = self.download_empty_db(store, fs(base_path=delme_drive_old_pext, files=fs_files_smb1_on_delme_old_pext(), folders=fs_folders_nes_on_delme_old_pext()))

        self.assertEqual(empty_store(base_path=delme_drive_old_pext), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_smb1_installed_on_delme_and_fat_and_config_with_base_path_delme___removes_smb1_only_on_delme(self):
        store = store_smb1_on_delme()

        sut = self.download_empty_db(store, fs(base_path=delme_drive_old_pext, folders=[*fs_folders_nes_on_delme_old_pext(), *fs_folders_nes_on_fat_old_pext()], files={**fs_files_smb1_on_delme_old_pext(), **fs_files_smb1_on_fat_old_pext()}))

        self.assertEqual(empty_store(delme_drive_old_pext), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_fat_old_pext(), files=fs_files_smb1_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_empty_db___with_nes_folder_installed_on_delme_and_fat_and_config_with_base_path_delme___removes_nes_folder_only_on_delme(self):
        store = store_nes_folder()
        del store[K_BASE_PATH]

        sut = self.download_empty_db(store, fs(base_path=delme_drive_old_pext, folders=[*fs_folders_nes_on_delme_old_pext(), *fs_folders_nes_on_fat_old_pext()]))

        self.assertEqual(empty_store(delme_drive_old_pext), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_pdfviewer_db___on_empty_setup_and_base_system_path_hidden___installs_pdfviewer_on_hidden(self):
        store = empty_test_store_old_pext()

        sut = self.download_pdfviewer_db(store, fs(config=config_with_old_pext(base_system_path=hidden_drive_old_pext)))

        self.assertEqual(store_pdfviewer_on_base_system_path_hidden(), store)
        self.assertEqual(fs_data(folders=fs_folders_pdfviewers_on_hidden_old_pext(), files=fs_files_pdfviewers_on_hidden_old_pext()), sut.fs_data)
        self.assertReports(sut, [FILE_PDFViewer])

    def test_download_empty_db___after_pdfviewer_was_installed_on_base_system_path_hidden___removes_pdfviewer_and_linux_folder(self):
        store = store_pdfviewer_on_base_system_path_hidden()

        sut = self.download_empty_db(store, fs(config=config_with_old_pext(base_system_path=hidden_drive_old_pext), folders=fs_folders_pdfviewers_on_hidden_old_pext(), files=fs_files_pdfviewers_on_hidden_old_pext()))

        self.assertEqual(empty_test_store_old_pext(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_contra___on_empty_store_and_nothing_on_fs___downloads_smb1_and_contra_on_fat(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_and_contra(store, fs())

        self.assertEqual(store_smb1_and_contra(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_contra_old_pext, file_nes_smb1_old_pext])

    def test_download_smb1_and_contra___after_previous_run___does_nothing(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_and_contra_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()))

        self.assertEqual(store_smb1_and_contra(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat_old_pext(), folders=fs_folders_nes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [], save=False)

    def test_download_smb1_and_contra___after_copying_contra_to_usb1___downloads_smb_to_usb1_and_validates_contra_on_usb1(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_and_contra_on_fat_contra_on_usb1_too_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_smb1_and_contra_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, downloaded=[file_nes_smb1_old_pext], validated=[file_nes_contra_old_pext])

    def test_download_empty_db___after_copied_contra_to_usb1___removes_everything_except_nes_folder_on_usb1(self):
        store = store_smb1_and_contra_on_fat_and_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_contra_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_contra___after_moving_contra_to_usb1___downloads_smb_to_usb1_and_validates_contra_on_usb1(self):
        store = store_smb1_and_contra()

        sut = self.download_smb1_and_contra(store, fs(files=fs_files_smb1_on_fat_contra_on_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_smb1_on_fat_and_smb1_and_contra_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, downloaded=[file_nes_smb1_old_pext], validated=[file_nes_contra_old_pext])

    def test_download_empty_db___after_moved_contra_to_usb1___removes_everything_except_games_and_nes_folder_on_usb1(self):
        store = store_smb1_on_fat_and_smb1_and_contra_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_nes_palettes___on_empty_setup___installs_smb1_and_nes_palettes_on_fat(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_and_palettes(store, fs())

        self.assertEqual(store_smb1_and_nes_palettes(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_nes_palettes_on_fat_old_pext(), folders=fs_folders_nes_palettes_on_fat_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext, file_nes_smb1_old_pext])

    def test_download_empty_db___after_installing_smb1_and_nes_on_fat___removes_everything(self):
        store = store_smb1_and_nes_palettes()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_fat_old_pext(), folders=fs_folders_nes_palettes_on_fat_old_pext()))

        self.assertEqual(empty_test_store_old_pext(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_and_nes_palettes___on_empty_store_with_nes_folder_on_usb1___installs_smb1_and_nes_palettes_on_usb1(self):
        store = empty_test_store_old_pext()

        sut = self.download_smb1_and_palettes(store, fs(folders=fs_folders_nes_on_usb1_old_pext()))

        self.assertEqual(store_smb1_and_nes_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_and_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_palette_a_old_pext, file_nes_smb1_old_pext])

    def test_download_empty_db___after_installing_smb1_and_nes_on_usb1___removes_everything_except_nes_folder_on_usb1(self):
        store = store_smb1_and_nes_palettes_on_usb1()

        sut = self.download_empty_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()))

        self.assertEqual(store_nes_folder_on_usb1(), store)
        self.assertEqual(fs_data(folders=fs_folders_nes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_smb1_in_db_test_and_nes_manual_in_db_demo___on_empty_stores_with_games_nes_folder_on_usb1_and_docs_nes_folder_on_usb2___installs_smb1_on_usb1_and_nes_manual_on_usb2(self):
        sut, local_store_dbs = self.download_smb1_in_db_test_and_nes_manual_in_db_demo(fs(folders=fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2_old_pext()))

        self.assertEqual(store_smb1_on_usb1_and_nes_manual_on_usb2(), local_store_dbs)
        self.assertEqual(fs_data(files=fs_files_smb1_on_usb1_and_nes_manual_on_usb2_old_pext(), folders=fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2_old_pext()), sut.fs_data)
        self.assertReports(sut, [file_nes_smb1_old_pext, file_nes_manual_old_pext])

    def test_download_external_drives_1_and_2___on_empty_stores_with_same_fs_as_system_tests___installs_at_expected_locations(self):
        external_folders = [
            media_usb0_old_pext(folder_games_old_pext),
            media_usb2_old_pext(folder_games_old_pext), media_usb2_old_pext(folder_games_nes_old_pext),

            media_usb0_old_pext(folder_docs_old_pext), media_usb0_old_pext(folder_docs_neogeo_old_pext),
            media_usb1_old_pext(folder_docs_old_pext), media_usb1_old_pext(folder_docs_s32x_old_pext),
            media_usb2_old_pext(folder_docs_old_pext),
        ]

        sut, local_store_dbs = self.download_external_drives_1_and_2(fs(config=config_with_old_pext(base_system_path=MEDIA_FAT), folders=external_folders))

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
                **_store_files_foo_old_pext(),
                media_usb0_old_pext(file_neogeo_md_old_pext): file_neogeo_md_descr_old_pext(),
                media_usb1_old_pext(file_s32x_md_old_pext): file_s32x_md_descr_old_pext(),
                **fs_files_smb1_and_contra_on_usb2_old_pext(),
            },
            folders=external_folders
        ), sut.fs_data)
        self.assertReports(sut, [file_foo_old_pext, file_neogeo_md_old_pext, file_s32x_md_old_pext, file_nes_smb1_old_pext, file_nes_contra_old_pext])

    def test_download_just_nes_palette_file_db___after_installing_smb1_and_nes_palettes_on_usb1___removes_everything_except_nes_palettes_on_usb1(self):
        store = store_smb1_and_nes_palettes_on_usb1()

        sut = self.download_just_nes_palette_file_db(store, fs(files=fs_files_smb1_and_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()))

        self.assertEqual(store_just_nes_palettes_on_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_nes_palettes_on_usb1_old_pext(), folders=fs_folders_nes_palettes_on_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_download_just_smb1_file_db___with_smb1_and_contra_on_fat_and_usb1___removes_contra_and_keeps_smb1_on_fat_and_usb1_with_its_folders(self):
        store = store_smb1_and_contra_on_fat_and_usb1()

        sut = self.download_just_smb1_file_db(store, fs(files=fs_files_smb1_and_contra_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()))

        self.assertEqual(store_smb1_on_fat_and_usb1(), store)
        self.assertEqual(fs_data(files=fs_files_smb1_on_fat_and_usb1_old_pext(), folders=fs_folders_nes_on_fat_and_usb1_old_pext()), sut.fs_data)
        self.assertReports(sut, [])

    def test_delme_download_three_dbs_with_sd_priority_files___on_empty_system_with_some_folders____installs_all_in_fat_except_md(self):
        sut, stores = self.download_three_dbs_with_sd_priority_files(
            with_fs=fs(
                folders=[folder_a_old_pext, folder_games_old_pext, folder_games_nes_old_pext, media_usb1_old_pext(folder_games_old_pext), media_usb1_old_pext(folder_games_md_old_pext)]
            )
        )
        self.assertSystem({
            "fs": fs_data(files=installed_three_dbs_fs_files(), folders=installed_three_dbs_fs_folders()),
            "stores": installed_three_dbs_store(),
            "ok": [file_a_old_pext, file_nes_smb1_old_pext, file_md_sonic_old_pext],
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
            fs(folders=[media_usb1_old_pext(folder_games_old_pext), media_fat_old_pext(folder_games_old_pext)]) if with_fs is None else with_fs,
            [db_test_with_file_a_old_pext(db_id='1'), db_smb1_old_pext(db_id='2'), db_sonic_old_pext(db_id='3')],
            input_stores=input_stores
        )


def fs(files=None, folders=None, base_path=None, config=None):
    return ImporterImplicitInputs(files=files, folders=folders, base_path=base_path, config=config)


def installed_three_dbs_fs_files(): return {**files_a_old_pext(), **fs_files_smb1_on_fat_old_pext(), **fs_files_sonic_on_usb1_old_pext()}
def installed_three_dbs_fs_folders(): return [folder_a_old_pext, folder_games_old_pext, folder_games_nes_old_pext, media_usb1_old_pext(folder_games_old_pext), media_usb1_old_pext(folder_games_md_old_pext)]
def installed_three_dbs_store(): return [store_test_with_file_a_descr(), store_smb1_on_fat(), store_sonic_on_usb1()]

