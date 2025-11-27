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

from downloader.constants import FILE_PDFViewer, FOLDER_linux, \
    DISTRIBUTION_MISTER_DB_ID
from test.fake_logger import NoLogger
from test.fake_logger import SpyLoggerDecorator
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_waiter import NoWaiter
from test.fake_file_system_factory import fs_data
from test.objects import store_with_folders, db_distribution_mister, db_test_being_empty_descr, file_boot_rom, \
    boot_rom_descr, with_overwrite, file_a_descr, file_a_updated_descr, \
    db_test_with_file, db_with_file, db_with_folders, file_a, folder_a, \
    store_test_with_file_a_descr, store_test_with_file, db_test_with_file_a, file_descr, empty_test_store, \
    file_pdfviewer_descr, store_descr, media_usb0, \
    db_entity, file_c_descr, file_abc, folder_ab, path_system, file_system_abc_descr, store_reboot_descr, file_reboot, \
    file_reboot_descr, db_test, db_reboot_descr
from test.fake_online_importer import OnlineImporter
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase


class TestOnlineImporter(OnlineImporterTestBase):

    def test_download_dbs_contents___with_trivial_db___does_nothing(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_test_being_empty_descr(), store).download()

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___being_empty___does_nothing(self):
        self.assertReportsNothing(OnlineImporter().download())

    def test_download_dbs_contents___with_one_file___fills_store_with_that_file(self):
        store = empty_test_store()

        sut = OnlineImporter()\
            .add_db(db_test_with_file_a(), store)\
            .download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_one_file___after_previous_identical_run___does_nothing(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter\
            .from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_test_with_file_a(), store)\
            .download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [], save=False)

    def test_download_one_file___with_a_store_containing_one_file_but_fs_nothing___restores_the_fs(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter()\
            .add_db(db_test_with_file_a(), store)\
            .download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False)

    def test_download_one_file___on_empty_store_but_fs_containing_a_file___restores_the_store(self):
        store = empty_test_store()

        sut = OnlineImporter \
            .from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_test_with_file_a(), store)\
            .download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_empty_db___with_a_store_containing_one_file_but_fs_nothing___cleans_up_store(self):
        store = store_test_with_file_a_descr()

        sut = OnlineImporter()\
            .add_db(db_entity(), store)\
            .download()

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReports(sut, [])

    def test_download_dbs_contents___with_existing_incorrect_file_but_correct_already_on_store___changes_nothing(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: {'hash': 'does_not_match'}}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: {'hash': 'does_not_match'}}, folders={folder_a: {}}), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___with_existing_incorrect_file_also_on_store___downloads_the_correct_one(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: {'hash': 'does_not_match', 'size': 0}}))
        store = store_test_with_file(file_a, {'hash': 'does_not_match', 'size': 0})

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_dbs_contents___with_non_existing_one_file_already_on_store___installs_file_regardless(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a], save=False)

    def test_download_dbs_contents___with_one_failed_file___just_reports_error(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(remote_failures={file_a: 99}))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(fs_data(folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_with_folders([folder_a]), store)
        self.assertReports(sut, [], errors=[file_a])

    def test_download_dbs_contents___with_file_with_wrong_hash___just_reports_error(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(remote_files={file_a: file_descr(hash_code="wrong_hash")}))
        store = empty_test_store()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(store_with_folders([folder_a]), store)
        self.assertEqual(fs_data(folders=[folder_a]), sut.fs_data)
        self.assertReports(sut, [], errors=[file_a])

    def test_download_dbs_contents__when_called_twice_on_trivial_db___does_nothing(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_test_being_empty_descr(), store).download()
        sut.add_db(db_test_being_empty_descr(), store).download()

        self.assertEqual(fs_data(), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut)

    def test_download_distribution_mister_with_pdfviewer___on_empty_store_and_fs___needs_reboot(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_distribution_mister(files={FILE_PDFViewer: file_pdfviewer_descr()}, folders={FOLDER_linux: {'path': 'system'}}), store)
        sut.download()

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

    def test_download_dbs_contents___with_stored_file_a_and_download_error___reports_error_but_store_and_fs_is_unchanged(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, storing_problems={file_a: 99}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(descr=file_a_updated_descr()), store)
        sut.download()

        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.file_system.data)
        self.assertReports(sut, [], errors=[file_a], save=False)

    def test_download_dbs_contents___with_duplicated_file___just_accounts_for_the_first_added(self):
        sut = OnlineImporter()
        store_test = empty_test_store()
        store_bar = empty_test_store()

        sut.add_db(db_with_file('test', file_a, file_a_descr()), store_test)
        sut.add_db(db_with_file('bar', file_a, file_a_updated_descr()), store_bar)
        sut.download()

        self.assertEqual(store_test_with_file(file_a, file_a_descr()), store_test)
        self.assertEqual(empty_test_store(), store_bar)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertReports(sut, [file_a])

    def test_download_dbs_contents___with_a_file_and_no_folders___still_creates_the_a_folder(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_with_file(db_test, file_a, file_a_descr()), store)
        sut.download()

        self.assertEqual(store_test_with_file(file_a, file_a_descr()), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertReports(sut, [file_a])

    def test_download_dbs_contents___with_folder_ab___still_creates_the_a_folder(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_with_folders(db_test, [folder_ab]), store)
        sut.download()

        self.assertEqual(store_with_folders([folder_ab], db_test), store)
        self.assertEqual(fs_data(folders={folder_a: {}, folder_ab: {}}), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_download_dbs_contents___when_file_a_gets_removed___store_and_fs_become_empty(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_being_empty_descr(), store)
        sut.download()

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_download_dbs_contents___when_file_is_already_there___does_nothing(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReportsNothing(sut)

    def test_download_dbs_contents___when_downloaded_file_is_missing___downloads_it_again(self):
        sut = OnlineImporter()
        store = store_test_with_file_a_descr()

        sut.add_db(db_test_with_file_a(), store)
        sut.download()

        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders={folder_a: {}}), sut.fs_data)
        self.assertReports(sut, [file_a], save=False)

    def test_overwrite___when_boot_rom_present___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_boot_rom: {"hash": "something_else"}}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_boot_rom, boot_rom_descr()), store)
        sut.download()

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(files={file_boot_rom: {"hash": "something_else"}}), sut.fs_data)
        self.assertReportsNothing(sut, skipped_updated_files={'test': [file_boot_rom]})

    def test_overwrite___when_boot_rom_present_but_with_different_case___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_boot_rom.upper(): {"hash": "something_else"}}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_boot_rom.lower(), boot_rom_descr()), store)
        sut.download()

        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(files={file_boot_rom: {"hash": "something_else"}}), sut.fs_data)
        self.assertReportsNothing(sut, skipped_updated_files={'test': [file_boot_rom]})

    def test_overwrite___when_overwrite_yes_file_a_is_present___should_not_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, with_overwrite(file_a_updated_descr(), True)), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_updated_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_descr(files={file_a: with_overwrite(file_a_updated_descr(), True)}), store)
        self.assertReports(sut, [file_a], skipped_updated_files={})

    def test_overwrite___when_on_empty_store_overwrite_no_file_a_is_present___should_not_overwrite_it_and_neither_fill_the_store(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, with_overwrite(file_a_updated_descr(), False)), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(empty_test_store(), store)
        self.assertReportsNothing(sut, skipped_updated_files={'test': [file_a]})

    def test_overwrite___when_file_a_without_overwrite_is_present___should_overwrite_it(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}))
        store = empty_test_store()

        sut.add_db(db_test_with_file(file_a, file_a_updated_descr()), store)
        sut.download()

        self.assertEqual(store_test_with_file(file_a, file_a_updated_descr()), store)
        self.assertEqual(fs_data(files={file_a: file_a_updated_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertReports(sut, [file_a], skipped_updated_files={})

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x_y___should_delete_b_c_and_store_x_y(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(folders=['a', 'b', 'c']))
        store1 = store_with_folders(['a', 'b', 'c'])

        sut.add_db(db_with_folders('db1', ['a', 'x', 'y']), store1)
        sut.download()

        self.assertEqual(store_with_folders(['a', 'x', 'y']), store1)
        self.assertEqual(fs_data(folders=['a', 'x', 'y']), sut.fs_data)
        self.assertReportsNothing(sut, save=True)

    def test_deleted_folders___when_db_1_has_a_b_c_and_store_1_has_a_x___and_db_2_has_b_and_store_2_is_empty__and_db_3_is_empty_and_store_3_has_z___should_delete_c_z_and_store_x(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(folders=['a', 'b', 'c', 'z']))
        store1 = store_with_folders(['a', 'b', 'c'])
        store2 = store_with_folders([])
        store3 = store_with_folders(['z'])

        sut.add_db(db_with_folders('db1', ['a', 'x']), store1)
        sut.add_db(db_with_folders('db2', ['b']), store2)
        sut.add_db(db_with_folders('db3', []), store3)
        sut.download()

        self.assertEqual(store_with_folders(['a', 'x']), store1)
        self.assertEqual(store_with_folders(['b']), store2)
        self.assertEqual(store_with_folders([]), store3)
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

        OnlineImporter(waiter=waiter, logger=logger).add_db(db, empty_test_store()).download()

        self.assertIn(expected_wait, waiter.registeredWaits)
        self.assertIn(expected_log, [line for call in logger.printCalls for line in call[0].split('\n') if line])

    def test_download_system_abc_db___after_already_been_installed___does_nothing(self):
        def store_file_abc(): return store_descr(files={file_abc: file_system_abc_descr()}, folders={folder_a: path_system(), folder_ab: path_system()})
        def fs_files_abc_on_usb0(): return {media_usb0(file_abc): file_c_descr()}
        def fs_folders_ab_on_usb0(): return [media_usb0(folder_a), media_usb0(folder_ab)]

        store = store_file_abc()

        db = db_entity(files={file_abc: file_system_abc_descr()})
        sut = self._download_db(db, store, fs(files=fs_files_abc_on_usb0(), folders=fs_folders_ab_on_usb0()))

        self.assertEqual(store_file_abc(), store)
        self.assertEqual(fs_data(files=fs_files_abc_on_usb0(), folders=fs_folders_ab_on_usb0()), sut.fs_data)
        self.assertReportsNothing(sut)

    def test_download_reboot_file___on_empty_store_and_fs___needs_reboot(self):
        sut = self.download_reboot_file(empty_test_store(), fs())
        self.assertReports(sut, [file_reboot], needs_reboot=True)

    def test_download_reboot_file___system_already_containing_it___needs_no_reboot(self):
        sut = self.download_reboot_file(store_reboot_descr(), fs(files={file_reboot: file_reboot_descr()}))
        self.assertReportsNothing(sut)

    def test_download_reboot_file___system_already_containing_it___needs_no_reboot2(self):
        sut = self.download_reboot_file(store_reboot_descr(custom_hash='other_hash'), fs(files={file_reboot: file_reboot_descr()}))
        self.assertReports(sut, [file_reboot], needs_reboot=True)

    def test_download_reboot_file_and_later_again___on_empty_store_and_fs___sut_keeps_needs_reboot_but_box_doesnt(self):
        sut = OnlineImporter().add_db(db_reboot_descr())

        sut.download()

        self.assertTrue(sut.box().needs_reboot())
        self.assertReports(sut, [file_reboot], needs_reboot=True)

        sut.download()

        self.assertFalse(sut.box().needs_reboot())
        self.assertReports(sut, [], needs_reboot=True, save=False)

    def test_removes_folder_slash_endings___on_empty_fs___registers_the_folder_without_the_ending_slash(self):
        sut = OnlineImporter()
        store = empty_test_store()

        sut.add_db(db_entity(files={file_a: file_a_descr()}, folders={folder_a + '/': {}}), store)
        sut.download()

        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store)
        self.assertReports(sut, [file_a])

    def test_download_db2_with_file_a_and_emtpy_db1___after_having_db1_with_file_a_and_empty_db2___updates_stores_but_no_changes_on_fs(self):
        store1 = empty_test_store()
        store2 = empty_test_store()

        sut = OnlineImporter()\
            .add_db(db_test_with_file_a(db_id='1'), store1)\
            .add_db(db_entity(db_id='2'), store2)\
            .download()

        self.assertEqual([
            {'data': '/media/fat/a', 'scope': 'make_dirs'},
            {'data': '/media/fat/a/a', 'scope': 'write_incoming_stream'}
        ], sut.fs_records)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store1)
        self.assertEqual(empty_test_store(), store2)
        self.assertReports(sut, [file_a])

        store1 = store_test_with_file_a_descr()
        store2 = empty_test_store()
        sut = OnlineImporter().from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_entity(db_id='1'), store1)\
            .add_db(db_test_with_file_a(db_id='2'), store2)\
            .download()

        self.assertEqual([{'data': '/media/fat/a', 'scope': 'make_dirs'}], sut.fs_records)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(empty_test_store(), store1)
        self.assertEqual(store_test_with_file_a_descr(), store2)
        self.assertReports(sut, [file_a])

    def test_download_db1_with_file_a_and_emtpy_db2___after_having_db2_with_file_a_and_empty_db1___updates_stores_but_no_changes_on_fs(self):
        store1 = empty_test_store()
        store2 = empty_test_store()

        sut = OnlineImporter()\
            .add_db(db_entity(db_id='1'), store1)\
            .add_db(db_test_with_file_a(db_id='2'), store2)\
            .download()

        self.assertEqual([
            {'data': '/media/fat/a', 'scope': 'make_dirs'},
            {'data': '/media/fat/a/a', 'scope': 'write_incoming_stream'},
        ], sut.fs_records)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(empty_test_store(), store1)
        self.assertEqual(store_test_with_file_a_descr(), store2)
        self.assertReports(sut, [file_a])

        sut = OnlineImporter().from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a]))\
            .add_db(db_test_with_file_a(db_id='1'), store1)\
            .add_db(db_entity(db_id='2'), store2)\
            .download()

        self.assertEqual([{'data': '/media/fat/a', 'scope': 'make_dirs'}], sut.fs_records)
        self.assertEqual(fs_data(files={file_a: file_a_descr()}, folders=[folder_a]), sut.fs_data)
        self.assertEqual(store_test_with_file_a_descr(), store1)
        self.assertEqual(empty_test_store(), store2)
        self.assertReports(sut, [file_a])



def fs(files=None, folders=None, base_path=None, config=None):
    return ImporterImplicitInputs(files=files, folders=folders, base_path=base_path, config=config)

