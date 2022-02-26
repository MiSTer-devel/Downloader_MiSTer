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

from downloader.constants import K_ZIP_FILE_COUNT_THRESHOLD
from downloader.online_importer import WrongDatabaseOptions
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data, FileSystemFactory
from test.objects import db_test_descr, store_test_descr, config_with_filter, empty_test_store
from test.fake_online_importer import OnlineImporter
from test.zip_objects import cheats_folder_zip_desc, cheats_folder_tag_dictionary, cheats_folder_id, \
    cheats_folder_nes_file_path, cheats_folder_nes_folder_name, cheats_folder_sms_file_path, \
    cheats_folder_sms_folder_name, \
    zipped_files_from_cheats_folder, summary_json_from_cheats_folder, cheats_folder_name, \
    cheats_folder_files, cheats_folder_folders, cheats_folder_sms_file_descr, cheats_folder_sms_folder_descr, \
    cheats_folder_descr, cheats_folder_nes_file_descr, cheats_folder_nes_folder_descr, cheats_folder_nes_file_hash, \
    cheats_folder_nes_file_size, cheats_folder_sms_file_hash, cheats_folder_sms_file_size


class TestOnlineImporterWithFiltersAndZips(unittest.TestCase):

    def test_download_zipped_cheats_folder___with_empty_store_and_negative_nes_filter___installs_filtered_nes_zip_data_and_only_sms_file(self):
        actual_store = self.download_zipped_cheats_folder(empty_test_store(), '!nes')

        self.assertEqual(store_with_filtered_nes_zip_data(), actual_store)
        self.assertOnlySmsFileIsInstalled()

    def test_download_zipped_cheats_folder___with_empty_store_and_negative_cheats_filter___installs_filtered_cheats_zip_data_but_no_files(self):
        actual_store = self.download_zipped_cheats_folder(empty_test_store(), '!cheats')

        self.assertEqual(store_with_filtered_cheats_zip_data(), actual_store)
        self.assertEqual(fs_data(), self.sut.fs_data)

    def test_download_zipped_cheats_folder___with_empty_store_and_filter_none___installs_zips_and_files(self):
        actual_store = self.download_zipped_cheats_folder(empty_test_store(), None)

        self.assertEqual(store_with_installed_files_and_zips_but_no_filtered_data(), actual_store)
        self.assertAllFilesAreInstalled()

    def test_download_zipped_cheats_folder___with_filtered_nes_zip_data_in_store_but_empty_filter___installs_files_and_removes_filtered_zip_data(self):
        actual_store = self.download_zipped_cheats_folder(store_with_filtered_nes_zip_data(), None)

        self.assertEqual(store_with_installed_files_and_zips_but_no_filtered_data(), actual_store)
        self.assertAllFilesAreInstalled()

    def test_download_zipped_cheats_folder___with_filtered_nes_zip_data_in_store_and_negative_cheats_filter___expands_zip_and_filtered_data_with_sms_and_installs_nothing(self):
        actual_store = self.download_zipped_cheats_folder(store_with_filtered_nes_zip_data(), '!cheats', implicit_inputs=ImporterImplicitInputs(
            files={cheats_folder_sms_file_path: cheats_folder_sms_folder_descr()},
        ))

        self.assertEqual(store_with_filtered_cheats_zip_data(), actual_store)
        self.assertEqual(fs_data(), self.sut.fs_data)

    def test_download_zipped_cheats_folder___with_filtered_nes_zip_data_in_store_and_negative_nes_filter___keeps_zip_and_filtered_data_and_installs_only_sms_file(self):
        actual_store = self.download_zipped_cheats_folder(store_with_filtered_nes_zip_data(), '!nes')

        self.assertEqual(store_with_filtered_nes_zip_data(), actual_store)
        self.assertOnlySmsFileIsInstalled()

    def test_download_zipped_cheats_folder___with_everything_already_on_store_but_new_summary_has_different_tags___updates_the_tags_in_the_store(self):
        actual_store = self.download_zipped_cheats_folder(
            store_with_cheats_non_filtered(),
            'all',
            implicit_inputs=ImporterImplicitInputs(files={
                cheats_folder_nes_file_path: {'hash': cheats_folder_nes_file_hash, 'size': cheats_folder_nes_file_size},
                cheats_folder_sms_file_path: {'hash': cheats_folder_sms_file_hash, 'size': cheats_folder_sms_file_size}
            }),
            summary=_append_tag_to_store('x', summary_json_from_cheats_folder()),
            summary_hash='different')

        self.assertEqual(store_with_cheats_non_filtered_and_filter_x(), actual_store)
        self.assertAllFilesAreInstalled()

    def test_download_cheat_files_without_zip___with_filtered_nes_zip_data_in_store_and_negative_nes_filter___removes_filtered_zip_data_and_installs_only_sms_file(self):
        actual_store = self.download_cheat_files_without_zip(store_with_filtered_nes_zip_data(), '!nes')

        self.assertEqual(store_with_sms_file_only(), actual_store)
        self.assertOnlySmsFileIsInstalled()

    def test_download_cheat_files_without_zip___with_filtered_nes_zip_data_in_store_and_negative_cheats_filter___removes_filtered_zip_data_and_installs_nothing(self):
        actual_store = self.download_cheat_files_without_zip(store_with_filtered_nes_zip_data(), '!cheats', file_system_factory=FileSystemFactory(files={cheats_folder_sms_file_path: {}}))

        self.assertEqual(empty_test_store(), actual_store)
        self.assertEqual(fs_data(), self.sut.fs_data)

    def test_download_cheat_files_without_zip___with_filtered_nes_zip_data_in_store_but_filter_none___install_files_and_removes_filtered_zip_data(self):
        actual_store = self.download_cheat_files_without_zip(store_with_filtered_nes_zip_data(), None)

        self.assertEqual(store_with_installed_files_without_zips_and_no_filtered_data(), actual_store)
        self.assertAllFilesAreInstalled()

    def test_download_cheat_files_without_zip___with_filtered_nes_zip_data_in_store_but_filter_empty_string___install_files_and_removes_filtered_zip_data(self):
        self.assertRaises(WrongDatabaseOptions, lambda: self.download_cheat_files_without_zip(store_with_filtered_nes_zip_data(), ''))

    def download_zipped_cheats_folder(self, store, filter_value, summary=None, summary_hash=None, implicit_inputs=None):
        implicit_inputs = implicit_inputs if implicit_inputs is not None else ImporterImplicitInputs()
        implicit_inputs.config = config_with_filter(filter_value)
        implicit_inputs.config[K_ZIP_FILE_COUNT_THRESHOLD] = 0  # This will cause to unzip the contents

        self.sut = OnlineImporter(implicit_inputs=implicit_inputs)

        summary = summary_json_from_cheats_folder() if summary is None else summary

        self.sut.add_db(db_test_descr(zips={
            cheats_folder_id: cheats_folder_zip_desc(zipped_files=zipped_files_from_cheats_folder(), summary=summary, summary_hash=summary_hash)
        }, tag_dictionary=cheats_folder_tag_dictionary()), store).download(False)

        return store

    def download_cheat_files_without_zip(self, store, filter_value, file_system_factory=None):
        self.sut = OnlineImporter(config=config_with_filter(filter_value), file_system_factory=file_system_factory)
        self.sut.add_db(db_test_descr(
            files=cheats_folder_files(zip_id=False),
            folders=cheats_folder_folders(zip_id=False),
            tag_dictionary=cheats_folder_tag_dictionary()),
            store).download(False)
        return store

    def assertOnlyNesFileIsInstalled(self):
        self.assertEqual(fs_data(
            files={cheats_folder_nes_file_path: {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size}},
            folders=[cheats_folder_name, cheats_folder_nes_folder_name]
        ), self.sut.fs_data)

    def assertOnlySmsFileIsInstalled(self):
        self.assertEqual(fs_data(
            files={cheats_folder_sms_file_path: {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size}},
            folders=[cheats_folder_name, cheats_folder_sms_folder_name]
        ), self.sut.fs_data)

    def assertAllFilesAreInstalled(self):
        self.assertEqual(fs_data(
            files={
                cheats_folder_sms_file_path: {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size},
                cheats_folder_nes_file_path: {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size}
            },
            folders=[cheats_folder_name, cheats_folder_sms_folder_name, cheats_folder_nes_folder_name]
        ), self.sut.fs_data)


def store_with_filtered_nes_zip_data():
    store = store_test_descr(zips={
        cheats_folder_id: cheats_folder_zip_desc()
    }, files={
        cheats_folder_sms_file_path: cheats_folder_sms_file_descr(url=False)
    }, folders={
        cheats_folder_sms_folder_name: cheats_folder_sms_folder_descr(),
        cheats_folder_name: cheats_folder_descr(),
    })

    store['filtered_zip_data'] = {
        cheats_folder_id: {
            'files': {
                cheats_folder_nes_file_path: cheats_folder_nes_file_descr(url=False)
            },
            'folders': {cheats_folder_nes_folder_name: cheats_folder_nes_folder_descr()}
        }
    }

    return store


def _append_tag_to_store(tag, store):
    for file in store['files']:
        store['files'][file]['tags'].append(tag)

    for folder in store['folders']:
        store['folders'][folder]['tags'].append(tag)

    return store


def store_with_cheats_non_filtered():
    store = store_test_descr(zips={
        cheats_folder_id: cheats_folder_zip_desc()
    }, files={
        cheats_folder_sms_file_path: cheats_folder_sms_file_descr(url=False),
        cheats_folder_nes_file_path: cheats_folder_nes_file_descr(url=False)
    }, folders={
        cheats_folder_sms_folder_name: cheats_folder_sms_folder_descr(),
        cheats_folder_nes_folder_name: cheats_folder_nes_folder_descr(),
        cheats_folder_name: cheats_folder_descr(),
    })

    return store


def store_with_cheats_non_filtered_and_filter_x():
    store = store_with_cheats_non_filtered()
    store['zips'][cheats_folder_id]['summary_file']['hash'] = 'different'
    return _append_tag_to_store('x', store)


def store_with_filtered_cheats_zip_data():
    store = store_test_descr(zips={
        cheats_folder_id: cheats_folder_zip_desc()
    })

    store['filtered_zip_data'] = {
        cheats_folder_id: summary_json_from_cheats_folder()
    }

    return store


def store_with_sms_file_only():
    return store_test_descr(files={
        cheats_folder_sms_file_path: cheats_folder_sms_file_descr(zip_id=False, tags=False)
    }, folders={
        cheats_folder_sms_folder_name: {},
        cheats_folder_name: {}
    })


def store_with_installed_files_and_zips_but_no_filtered_data():
    store = store_test_descr(zips={
        cheats_folder_id: cheats_folder_zip_desc()
    }, files=cheats_folder_files(url=False), folders=cheats_folder_folders())
    return store


def store_with_installed_files_without_zips_and_no_filtered_data():
    return store_test_descr(files=cheats_folder_files(zip_id=False, tags=False), folders=cheats_folder_folders(zip_id=False, tags=False))
