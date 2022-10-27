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
from downloader.constants import FILE_MiSTer_old, FILE_MiSTer, FILE_PDFViewer, FILE_MiSTer_new, FOLDER_linux, \
    DISTRIBUTION_MISTER_DB_ID
from test.fake_logger import SpyLoggerDecorator, NoLogger
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_waiter import NoWaiter
from test.fake_file_system_factory import fs_data, fs_records
from test.objects import store_with_folders, db_distribution_mister, db_test_being_empty_descr, file_boot_rom, \
    boot_rom_descr, with_overwrite, file_mister_descr, file_a_descr, file_a_updated_descr, \
    db_test_with_file, db_with_file, db_with_folders, file_a, folder_a, \
    store_test_with_file_a_descr, store_test_with_file, db_test_with_file_a, file_descr, empty_test_store, \
    file_pdfviewer_descr, store_descr, hash_MiSTer_old, db_test, media_usb0, \
    remove_all_priority_paths, db_entity
from test.fake_online_importer import OnlineImporter


class TestOnlineImporter(unittest.TestCase):

    def test_download_dbs_contents___with_trivial_db___does_nothing(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_test_being_empty_descr(), store).download(False)

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___being_empty___does_nothing(self):
        self.assertReportsNothing(OnlineImporter().download(False))

    def test_download_dbs_contents___with_one_file___fills_store_with_that_file(self):
        store = empty_test_store()

        sut = OnlineImporter()\
            .add_db(db_test_with_file_a(), store)\
            .download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_one_file___after_previous_identical_run___does_nothing(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter\
            .from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_test_with_file_a(), store)\
            .download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False)

    def test_download_one_file___with_a_store_containing_one_file_but_fs_nothing___restores_the_fs(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter()\
            .add_db(db_test_with_file_a(), store)\
            .download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False)

    def test_download_one_file___on_empty_store_but_fs_containing_a_file___restores_the_store(self):
        store = empty_test_store()

        sut = OnlineImporter \
            .from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_test_with_file_a(), store)\
            .download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_empty_db___with_a_store_containing_one_file_but_fs_nothing___cleans_up_store(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter()\
            .add_db(db_entity(), store)\
            .download(False)

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [])

    def test_download_dbs_contents___with_existing_incorrect_file_but_correct_already_on_store___changes_nothing(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: {'hash': 'does_not_match'}}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: {'hash': 'does_not_match'}}, folders={folder_a: {}}), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___with_existing_incorrect_file_also_on_store___downloads_the_correct_one(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: {'hash': 'does_not_match'}}))
        store = store_test_with_file(file_a, {'hash': 'does_not_match'})

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_dbs_contents___with_non_existing_one_file_already_on_store___installs_file_regardless(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False)

    def test_download_dbs_contents___with_one_failed_file___just_reports_error(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(remote_failures={file_a: 99}))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(fs_data(folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_with_folders(db_test, [folder_a]), store)
        self.assertReports(sut, [], errors=[file_a])

    def test_download_dbs_contents___with_file_with_wrong_hash___just_reports_error(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(remote_files={file_a: file_descr(hash_code="wrong_hash")}))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(store_with_folders(db_test, [folder_a]), store)
        self.assertEqual(fs_data(folders=[folder_a]), sut.fs_data)
        self.assertReports(sut, [], errors=[file_a])

    def test_download_dbs_contents__when_called_twice_on_trivial_db___does_nothing(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_test_being_empty_descr(), store).download(False)
        sut.add_db(db_test_being_empty_descr(), store).download(False)

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut)

    def test_download_distribution_mister_with_mister___on_empty_store___needs_reboot(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(
            files={media_usb0(FILE_MiSTer): {'hash': hash_MiSTer_old}},
        ))
        store = empty_test_store()

        sut.add_db(db_distribution_mister(files={FILE_MiSTer: file_mister_descr()}), store)
        sut.download(False)

        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr()}), store)
        self.assertEqual(fs_data(
            files={
                media_usb0(FILE_MiSTer): file_mister_descr(),
                media_usb0(FILE_MiSTer_old): {'hash': hash_MiSTer_old}
            },
        ), sut.fs_data)
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer), media_usb0(FILE_MiSTer_old))},
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer_new), media_usb0(FILE_MiSTer))},
        ]), sut.fs_records)
        self.assertReports(sut, [FILE_MiSTer], needs_reboot=True)

    def test_download_distribution_mister_with_pdfviewer___on_empty_store_and_fs___needs_reboot(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_distribution_mister(files={FILE_PDFViewer: file_pdfviewer_descr()}, folders={FOLDER_linux: {'path': 'system'}}), store)
        sut.download(False)

        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={
            FILE_PDFViewer: file_pdfviewer_descr()
        }, folders={
            FOLDER_linux: {'path': 'system'}
        }), store)
        self.assertEqual(fs_data(
            files={media_usb0(FILE_PDFViewer): file_pdfviewer_descr()},
            folders=[media_usb0(FOLDER_linux)],
        ), sut.fs_data)
        self.assertReports(sut, [FILE_PDFViewer], needs_reboot=False)

    def test_download_dbs_contents___with_stored_file_a_and_download_error___store_deletes_file_a_but_not_folder_a_and_fs_is_unchanged(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, storing_problems={file_a: 99}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(file_a_updated_descr()), store)
        sut.download(False)

        self.assertEqual(store_with_folders(db_test, [folder_a]), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.file_system.data)
        self.assertReports(sut, [], errors=[file_a])

    def test_download_dbs_contents___with_duplicated_file___just_accounts_for_the_first_added(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_with_file('test', file_a, file_a_descr()), store)
        sut.add_db(db_with_file('bar', file_a, file_a_updated_descr()), store)
        sut.download(False)

        self.assertEqual(store_test_with_file(file_a, file_a_descr()), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertReports(sut, [file_a])

    def test_download_dbs_contents___when_file_a_gets_removed___store_and_fs_become_empty(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_being_empty_descr(), store)
        sut.download(False)

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_download_dbs_contents___when_file_is_already_there___does_nothing(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___when_downloaded_file_is_missing___downloads_it_again(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download(False)

        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertReports(sut, [file_a], save=False)

    def test_overwrite___when_boot_rom_present___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_boot_rom: {"hash": "something_else"}}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_boot_rom, boot_rom_descr()), store)
        sut.download(False)

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(files={file_boot_rom: {"hash": "something_else"}}), sut.fs_data)
        self.assertEqual([file_boot_rom], sut.new_files_not_overwritten()['test'])
        self.assertReportsNothing(sut)

    def test_overwrite___when_boot_rom_present_but_with_different_case___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_boot_rom.upper(): {"hash": "something_else"}}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_boot_rom.lower(), boot_rom_descr()), store)
        sut.download(False)

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(files={file_boot_rom: {"hash": "something_else"}}), sut.fs_data)
        self.assertEqual([file_boot_rom], sut.new_files_not_overwritten()['test'])
        self.assertReportsNothing(sut)

    def test_overwrite___when_overwrite_yes_file_a_is_present___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, with_overwrite(file_a_updated_descr(), True)), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: file_a_updated_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_descr(files={file_a: with_overwrite(file_a_updated_descr(), True)}), store)
        self.assertReports(sut, [file_a])
        self.assertEqual({}, sut.new_files_not_overwritten())

    def test_overwrite___when_on_empty_store_overwrite_no_file_a_is_present___should_not_overwrite_it_and_neither_fill_the_store(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, with_overwrite(file_a_updated_descr(), False)), store)
        sut.download(False)

        self.assertEqual(fs_data(files={file_a: file_a_descr()}), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut)
        self.assertEqual([file_a], sut.new_files_not_overwritten()['test'])

    def test_overwrite___when_file_a_without_overwrite_is_present___should_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, file_a_updated_descr()), store)
        sut.download(False)

        self.assertEqual(store_test_with_file(file_a, file_a_updated_descr()), store)
        self.assertEqual(fs_data(files={file_a: file_a_updated_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual({}, sut.new_files_not_overwritten())
        self.assertReports(sut, [file_a])

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x_y___should_delete_b_c_and_store_x_y(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(folders=['a', 'b', 'c']))
        store1 = store_with_folders('db1', ['a', 'b', 'c'])

        sut.add_db(db_with_folders('db1', ['a', 'x', 'y']), store1)
        sut.download(False)

        self.assertEqual(store_with_folders('db1', ['a', 'x', 'y']), store1)
        self.assertEqual(fs_data(folders=['a', 'x', 'y']), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x___and_db_2_has_b_and_store_2_is_empty__and_db_3_is_empty_and_store_3_has_z___should_delete_c_z_and_store_x(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(folders=['a', 'b', 'c', 'z']))
        store1 = store_with_folders('db1', ['a', 'b', 'c'])
        store2 = store_with_folders('db2', [])
        store3 = store_with_folders('db3', ['z'])

        sut.add_db(db_with_folders('db1', ['a', 'x']), store1)
        sut.add_db(db_with_folders('db2', ['b']), store2)
        sut.add_db(db_with_folders('db3', []), store3)
        sut.download(False)

        self.assertEqual(store_with_folders('db1', ['a', 'x']), store1)
        self.assertEqual(store_with_folders('db2', ['b']), store2)
        self.assertEqual(store_with_folders('db3', []), store3)
        self.assertEqual(fs_data(folders=['a', 'b', 'x']), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_db_header___when_existing___send_the_lines_to_logger_and_waiter_accordingly(self):
        expected_log = 'this_is_the_logger_expected_log'
        expected_wait = 9999999.9

        waiter = NoWaiter()
        logger = SpyLoggerDecorator(NoLogger())

        db = db_test_being_empty_descr()
        db.header.append(expected_log)
        db.header.append(expected_wait)

        OnlineImporter(waiter=waiter, logger=logger).add_db(db, empty_test_store()).download(False)

        self.assertIn(expected_wait, waiter.registeredWaits)
        self.assertIn((expected_log,), logger.printCalls)

    def assertReportsNothing(self, sut, save=False):
        self.assertReports(sut, [], save=save)

    def assertReports(self, sut, installed, errors=None, needs_reboot=False, save=True):
        if errors is None:
            errors = []
        self.assertEqual(remove_all_priority_paths(installed), sut.correctly_installed_files())
        self.assertEqual(remove_all_priority_paths(errors), sut.files_that_failed())
        self.assertEqual(needs_reboot, sut.needs_reboot())
        self.assertEqual(save, sut.needs_save)


def downloaded_single_db(db, store=None, full_resync=False):
    sut = OnlineImporter()
    sut.add_db(db, store if store is not None else empty_test_store())
    sut.download(full_resync)
