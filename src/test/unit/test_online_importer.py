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
from downloader.config import default_config
from downloader.constants import file_MiSTer_old, file_MiSTer, file_PDFViewer, file_MiSTer_new
from downloader.other import empty_store
from downloader.online_importer import InvalidDownloaderPath, invalid_folders, invalid_paths, no_distribution_mister_invalid_paths
from test.fake_file_system import FileSystem
from test.objects import store_with_folders, db_distribution_mister_with_file, db_test_being_empty_descr, file_boot_rom, \
    boot_rom_descr, overwrite_file, file_mister_descr, file_a_descr, file_a_updated_descr, \
    db_test_with_file, db_with_file, db_with_folders, file_a, folder_a, \
    store_test_with_file_a_descr, store_test_with_file, db_test_with_file_a, file_descr, empty_test_store, \
    file_pdfviewer_descr
from test.fake_online_importer import OnlineImporter
from test.factory_stub import FactoryStub
from test.fake_file_downloader import FileDownloader


class TestOnlineImporter(unittest.TestCase):

    def test_download_dbs_contents___with_trivial_db___does_nothing(self):
        sut = OnlineImporter()
        store = empty_test_store()

        self.assertReportsNothing(sut.add_db(db_test_being_empty_descr(), store).download(False))
        self.assertEqualDict(store, empty_test_store())

    def test_download_dbs_contents___being_empty___does_nothing(self):
        self.assertReportsNothing(OnlineImporter().download(False))

    def test_download_dbs_contents___with_one_file___fills_store_with_that_file(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_a: file_a_descr()})
        self.assertHasFolderA(store)
        self.assertReports(sut, [file_a])
        self.assertTrue(sut.file_system.is_file(file_a))
        self.assertEqual([], sut.file_system.system_paths)

    def test_download_dbs_contents___with_existing_incorrect_file_but_correct_already_on_store___changes_nothing(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a({'hash': 'does_not_match'})
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_a: file_a_descr()})
        self.assertHasFolderA(store)
        self.assertReportsNothing(sut)
        self.assertEqual(sut.file_system.hash(file_a), 'does_not_match')
        self.assertNoRemovedFilesAndFolders(sut)

    def test_download_dbs_contents___with_existing_incorrect_file_also_on_store___downloads_the_correct_one(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a({'hash': 'does_not_match'})
        store = store_test_with_file(file_a, {'hash': 'does_not_match'})

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_a: file_a_descr()})
        self.assertHasFolderA(store)
        self.assertReports(sut, [file_a])
        self.assertEqual(sut.file_system.hash(file_a), file_a)
        self.assertEqual([], sut.file_system.removed_folders)
        self.assertEqual([], [f for f in sut.file_system.removed_files if not f.startswith('unique_temp_file')])

    def test_download_dbs_contents___with_non_existing_one_file_already_on_store___installs_file_regardless(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_a: file_a_descr()})
        self.assertHasFolderA(store)
        self.assertReports(sut, [file_a])
        self.assertTrue(sut.file_system.is_file(file_a))

    def test_download_dbs_contents___with_one_failed_file___just_reports_error(self):
        sut = online_importer_with_custom_file_downloader(lambda fd: fd.test_data.errors_at(file_a))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEmptyFiles(store)
        self.assertHasFolderA(store)
        self.assertReports(sut, [], errors=[file_a])
        self.assertFalse(sut.file_system.is_file(file_a))

    def test_download_dbs_contents___with_file_with_wrong_hash___just_reports_error(self):
        sut = online_importer_with_custom_file_downloader(lambda fd: fd.test_data.brings_file(file_a, file_descr(hash_code="wrong_hash")))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEmptyFiles(store)
        self.assertHasFolderA(store)
        self.assertReports(sut, [], errors=[file_a])
        self.assertFalse(sut.file_system.is_file(file_a))

    def test_download_distribution_mister___with_mister___needs_reboot(self):
        sut = OnlineImporter()
        store = empty_test_store()
        sut.file_system.test_data.with_old_mister_binary()

        sut.add_db(db_distribution_mister_with_file(file_MiSTer, file_mister_descr()), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_MiSTer: file_mister_descr()})
        self.assertEmptyFolders(store)
        self.assertReports(sut, [file_MiSTer], needs_reboot=True)
        self.assertTrue(sut.file_system.is_file(file_MiSTer))
        self.assertTrue(sut.file_system.is_file(file_MiSTer_old))
        self.assertEqual([file_MiSTer, file_MiSTer_new, file_MiSTer_old], sut.file_system.system_paths)

    def test_download_distribution_mister___with_pdfviewer___needs_reboot(self):
        sut = OnlineImporter()
        store = empty_test_store()
        sut.file_system.test_data.with_old_mister_binary()

        sut.add_db(db_distribution_mister_with_file(file_PDFViewer, file_pdfviewer_descr()), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_PDFViewer: file_pdfviewer_descr()})
        self.assertEmptyFolders(store)
        self.assertReports(sut, [file_PDFViewer], needs_reboot=False)
        self.assertTrue(sut.file_system.is_file(file_PDFViewer))
        self.assertEqual([file_PDFViewer], sut.file_system.system_paths)

    def test_download_test_db___with_mister___raises_invalid_downloader_path_exception(self):
        sut = OnlineImporter()
        store = empty_test_store()
        sut.file_system.test_data.with_old_mister_binary()

        sut.add_db(db_test_with_file(file_MiSTer, file_mister_descr()), store)
        self.assertRaises(InvalidDownloaderPath, lambda: sut.download(False))

        self.assertEqualDict(store, empty_test_store())
        self.assertEmptyFolders(store)
        self.assertReportsNothing(sut)
        self.assertTrue(sut.file_system.is_file(file_MiSTer))
        self.assertFalse(sut.file_system.is_file(file_MiSTer_old))
        self.assertEqual([], sut.file_system.system_paths)

    def test_download_dbs_contents___with_stored_file_a_and_download_error___store_deletes_file_a_but_not_folder_a_and_fs_is_unchanged(self):
        sut = online_importer_with_custom_file_downloader(lambda fd: fd.test_data.errors_at(file_a))
        sut.file_system.test_data.with_file_a()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(file_a_updated_descr()), store)
        sut.download(False)

        self.assertReports(sut, [], errors=[file_a])
        self.assertEmptyFiles(store)
        self.assertHasFolderA(store)
        self.assertTrue(sut.file_system.is_file(file_a))
        self.assertNoRemovedFilesAndFolders(sut)

    def test_download_dbs_contents___with_duplicated_file___just_accounts_for_the_first_added(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_with_file('test', file_a, file_a_descr()), store)
        sut.add_db(db_with_file('bar', file_a, file_a_updated_descr()), store)
        sut.download(False)

        self.assertEqualDict(store['files'], {file_a: file_a_descr()})
        self.assertEmptyFolders(store)
        self.assertReports(sut, [file_a])
        self.assertEqual(sut.file_system.hash(file_a), file_a_descr()['hash'])

    def test_download_dbs_contents___when_file_a_gets_removed___store_and_fs_become_empty(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a()
        sut.file_system.test_data.with_folders(['a'])
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_being_empty_descr(), store)
        sut.download(False)

        self.assertEmptyFiles(store)
        self.assertEmptyFolders(store)
        self.assertReportsNothing(sut)
        self.assertFalse(sut.file_system.is_file(file_a))
        self.assertEqual(sut.file_system.removed_files, [file_a])
        self.assertEqual(sut.file_system.removed_folders, [folder_a])

    def test_download_dbs_contents___when_file_is_already_there___does_nothing(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertHasFolderA(store)
        self.assertReportsNothing(sut)
        self.assertTrue(sut.file_system.is_file(file_a))

    def test_download_dbs_contents___when_downloaded_file_is_missing___downloads_it_again(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertHasFolderA(store)
        self.assertReports(sut, [file_a])
        self.assertTrue(sut.file_system.is_file(file_a))

    def test_download_dbs_contents___when_no_check_downloaded_files_and_downloaded_file_is_missing___does_nothing(self):
        config = default_config()
        config['check_manually_deleted_files'] = False
        sut = OnlineImporter(config=config)
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertHasFolderA(store)
        self.assertReportsNothing(sut)
        self.assertFalse(sut.file_system.is_file(file_a))

    def test_overwrite___when_boot_rom_present___should_not_overwrite_it(self):
        sut = OnlineImporter()
        store = empty_test_store()
        sut.file_system.test_data.with_file(file_boot_rom, {"hash": "something_else"})

        sut.add_db(db_test_with_file(file_boot_rom, boot_rom_descr()), store)
        sut.download(False)

        self.assertEmptyFolders(store)
        self.assertReportsNothing(sut)
        self.assertEqual("something_else", sut.file_system.hash(file_boot_rom))
        self.assertEqual([file_boot_rom], sut.new_files_not_overwritten()['test'])

    def test_overwrite___when_boot_rom_present_but_with_different_case___should_not_overwrite_it(self):
        sut = OnlineImporter()
        store = empty_test_store()
        sut.file_system.test_data.with_file(file_boot_rom.upper(), {"hash": "something_else"})

        sut.add_db(db_test_with_file(file_boot_rom.lower(), boot_rom_descr()), store)
        sut.download(False)

        actual_boot_rom_hash = sut.file_system.hash(file_boot_rom.lower())

        self.assertEmptyFolders(store)
        self.assertReportsNothing(sut)
        self.assertEqual("something_else", actual_boot_rom_hash)
        self.assertNotEqual(boot_rom_descr()['hash'], actual_boot_rom_hash)
        self.assertEqual([file_boot_rom], sut.new_files_not_overwritten()['test'])

    def test_overwrite___when_overwrite_yes_file_a_is_present___should_not_overwrite_it(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a()
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, overwrite_file(file_a_updated_descr(), True)), store)
        sut.download(False)

        actual_hash_file_a = sut.file_system.hash(file_a)

        self.assertEmptyFolders(store)
        self.assertReports(sut, [file_a])
        self.assertEqual(file_a_updated_descr()['hash'], actual_hash_file_a)
        self.assertNotEqual(file_a_descr()['hash'], actual_hash_file_a)
        self.assertEqual({}, sut.new_files_not_overwritten())

    def test_overwrite___when_on_empty_store_overwrite_no_file_a_is_present___should_not_overwrite_it_but_fill_the_store(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a()
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, overwrite_file(file_a_updated_descr(), False)), store)
        sut.download(False)

        actual_hash_file_a = sut.file_system.hash(file_a)

        self.assertEmptyFolders(store)
        self.assertReportsNothing(sut)
        self.assertEqual(file_a_descr()['hash'], actual_hash_file_a)
        self.assertNotEqual(file_a_updated_descr()['hash'], actual_hash_file_a)
        self.assertEqual([file_a], sut.new_files_not_overwritten()['test'])

    def test_overwrite___when_file_a_without_overwrite_is_present___should_overwrite_it(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_file_a()
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, file_a_updated_descr()), store)
        sut.download(False)

        actual_hash_file_a = sut.file_system.hash(file_a)

        self.assertEmptyFolders(store)
        self.assertReports(sut, [file_a])
        self.assertEqual(file_a_updated_descr()['hash'], actual_hash_file_a)
        self.assertNotEqual(file_a_descr()['hash'], actual_hash_file_a)
        self.assertEqual({}, sut.new_files_not_overwritten())

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x_y___should_delete_b_c_and_store_x_y(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_folders(['a', 'b', 'c'])
        store1 = store_with_folders('db1', ['a', 'b', 'c'])

        sut.add_db(db_with_folders('db1', ['a', 'x', 'y']), store1)
        sut.download(False)

        self.assertEqualDict(store1['folders'], ['a', 'x', 'y'])
        self.assertReportsNothing(sut)
        self.assertEqual(sut.file_system.folders(), ['a', 'x', 'y'])

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x___and_db_2_has_b_and_store_2_is_empty__and_db_3_is_empty_and_store_3_has_z___should_delete_c_z_and_store_x(self):
        sut = OnlineImporter()
        sut.file_system.test_data.with_folders(['a', 'b', 'c', 'z'])
        store1 = store_with_folders('db1', ['a', 'b', 'c'])
        store2 = store_with_folders('db2', [])
        store3 = store_with_folders('db3', ['z'])

        sut.add_db(db_with_folders('db1', ['a', 'x']), store1)
        sut.add_db(db_with_folders('db2', ['b']), store2)
        sut.add_db(db_with_folders('db3', []), store3)
        sut.download(False)

        self.assertEqualDict(store1['folders'], ['a', 'x'])
        self.assertEqualDict(store2['folders'], ['b'])
        self.assertEqualDict(store3['folders'], [])
        self.assertReportsNothing(sut)
        self.assertEqual(sut.file_system.folders(), ['a', 'b', 'x'])

    def test_downloaded_single_db___with_invalid_files___raises_error(self):
        invalids = [0, 'linux/file.txt', 'linux/something/something/file.txt', '../omg.txt', 'this/is/ok/../or/nope.txt', '/tmp/no', '.hidden'] + \
                        ['%s/file.txt' % k for k in invalid_folders()] + \
                        list(invalid_paths()) + \
                        list(no_distribution_mister_invalid_paths())

        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertRaises(InvalidDownloaderPath, lambda: downloaded_single_db(db_test_with_file(wrong_path, file_a_descr())))

    def test_downloaded_single_db___with_invalid_folders___raises_error(self):
        invalids = ('linux/f', 'linux/something/something/', '../', 'this/is/ok/../or/', '/user/', '.config/') + invalid_folders()
        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertRaises(InvalidDownloaderPath, lambda: downloaded_single_db(db_with_folders('wrong_db', {wrong_path: {}})))

    def assertEqualDict(self, store, o):
        if isinstance(o, list):
            o = {i: {} for i in o}
        self.assertEqual(o, store)

    def assertEmptyFolders(self, store):
        self.assertEqualDict(store['folders'], [])

    def assertHasFolderA(self, store):
        self.assertEqualDict(store['folders'], [folder_a])

    def assertEmptyFiles(self, store):
        self.assertEqualDict(store['files'], {})

    def assertReportsNothing(self, sut):
        self.assertReports(sut, [])

    def assertReports(self, sut, installed, errors=None, needs_reboot=False):
        if errors is None:
            errors = []
        self.assertEqual(installed, sut.correctly_installed_files())
        self.assertEqual(errors, sut.files_that_failed())
        self.assertEqual(needs_reboot, sut.needs_reboot())

    def assertNoRemovedFiles(self, sut):
        self.assertEqual(sut.file_system.removed_files, [])

    def assertNoRemovedFolders(self, sut):
        self.assertEqual(sut.file_system.removed_folders, [])

    def assertNoRemovedFilesAndFolders(self, sut):
        self.assertEqual([], sut.file_system.removed_folders)
        self.assertEqual([], sut.file_system.removed_files)


def downloaded_single_db(db, store=None, full_resync=False):
    sut = OnlineImporter()
    sut.add_db(db, store if store is not None else empty_test_store())
    sut.download(full_resync)


def online_importer_with_custom_file_downloader(func):
    file_system = FileSystem()
    return OnlineImporter(FactoryStub(FileDownloader(file_system=file_system)).has(func), file_system=file_system)
