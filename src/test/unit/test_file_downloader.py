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

from downloader.constants import FILE_MiSTer, FILE_MiSTer_new, FILE_MiSTer_old
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from downloader.target_path_repository import downloader_in_progress_postfix
from test.fake_store_migrator import StoreMigrator
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_importer_implicit_inputs import NetworkState, FileSystemState
from test.fake_logger import NoLogger
from test.fake_file_system_factory import fs_data, FileSystemFactory, fs_records
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.objects import file_menu_rbf, hash_menu_rbf, file_one, hash_one, hash_big, file_big, \
    hash_updated_big, big_size, config_with, file_mister_descr, hash_MiSTer_old, hash_MiSTer


def on_installed(path):
    return '/installed/' + path


def on_installed_system(path):
    return '/installed_system/' + path


def on_tmp(path):
    return '/tmp/' + path


class TestFileDownloader(unittest.TestCase):

    installed_path = '/installed'
    installed_system_path = '/installed_system'

    def setUp(self) -> None:
        config = config_with(base_path=self.installed_path, base_system_path=self.installed_system_path)
        self.network_state = NetworkState()
        self.file_system_state = FileSystemState(config=config)
        self.file_system_state.set_non_base_path(self.installed_system_path, FILE_MiSTer)
        self.file_system_state.set_non_base_path(self.installed_system_path, FILE_MiSTer_new)
        self.file_system_state.set_non_base_path(self.installed_system_path, FILE_MiSTer_old)
        file_system_factory = FileSystemFactory(state=self.file_system_state)
        self.file_downloader_factory = FileDownloaderFactory(file_system_factory=file_system_factory, network_state=self.network_state)
        self.file_system = file_system_factory.create_for_config(config)
        external_drives_repository = ExternalDrivesRepository(file_system=self.file_system)
        self.local_repository = ProductionLocalRepository(config, NoLogger(), self.file_system, StoreMigrator(), external_drives_repository)
        self.sut = self.file_downloader_factory.create(config, True)

    def test_download_nothing___from_scratch_no_issues___nothing_downloaded_no_errors(self):
        self.sut.download_files(False)
        self.assertDownloaded([])

    def test_download_files_one___from_scratch_no_issues___returns_correctly_downloaded_one_and_no_errors(self):
        self.download_one()
        self.assertDownloaded([file_one], [file_one])
        self.assertTrue(self.file_system.is_file(on_installed(file_one)))

    def test_download_files_one___from_scratch_with_retry___returns_correctly_downloaded_one_and_no_errors(self):
        self.network_state.remote_failures[file_one] = 2
        self.download_one()
        self.assertDownloaded([file_one], [file_one, file_one])

    def test_download_big_file___when_big_file_already_present_with_different_hash___gets_downloaded_through_a_downloader_in_progress_file_and_then_correctly_installed(self):
        downloader_in_progress_file = file_big + downloader_in_progress_postfix
        self.file_system_state.add_file(self.installed_path, file_big, {'hash': hash_big})

        self.download_big_file(hash_updated_big)
        self.assertEqual(
            fs_data(
                files={file_big: {'hash': hash_updated_big, 'size': big_size}},
                base_path='/installed'
            ),
            self.file_system.data
        )
        self.assertEqual([
            {"scope": "copy", "data": [on_installed(downloader_in_progress_file), on_installed(file_big)]},
            {"scope": "unlink", "data": on_installed(downloader_in_progress_file)},
        ], self.file_system.write_records)

    def test_download_files_one___from_scratch_could_not_download___return_errors(self):
        self.network_state.remote_failures[file_one] = 99
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_files_one___from_scratch_no_matching_hash___return_errors(self):
        self.network_state.remote_files[file_one] = {'hash': 'wrong',  'size': 1}
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_files_one___from_scratch_no_file_exists___return_errors(self):
        self.network_state.storing_problems.add(file_one)
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_reboot_file___from_scratch_no_issues___needs_reboot(self):
        self.file_system_state.set_non_base_path(self.installed_system_path, file_menu_rbf)
        self.download_reboot()
        self.assertDownloaded([file_menu_rbf], [file_menu_rbf], need_reboot=True)
        self.assertTrue(self.file_system.is_file(on_installed_system(file_menu_rbf)))

    def test_download_reboot_file___update_no_issues___needs_reboot(self):
        self.file_system_state.add_file(self.installed_system_path, file_menu_rbf, {'hash': 'old', 'size': 23})
        self.download_reboot()
        self.assertDownloaded([file_menu_rbf], [file_menu_rbf], need_reboot=True)
        self.assertEqual(fs_records([
            {'data': on_tmp('unique_temp_filename_0'), 'scope': 'unique_temp_filename'},
            {'data': [on_tmp('unique_temp_filename_0'), on_installed_system('menu.rbf')], 'scope': 'copy'},
            {'data': on_tmp('unique_temp_filename_0'), 'scope': 'unlink'}
        ]), self.file_system.write_records)

    def test_download_reboot_file___no_changes_no_issues___no_need_to_reboot(self):
        self.file_system_state.add_file(self.installed_system_path, file_menu_rbf, {'hash': hash_menu_rbf})

        self.download_reboot()
        self.assertDownloaded([file_menu_rbf])

    def test_download_mister_file___with_old_mister_file_present___stores_it_as_mister_and_moves_old_one_to_mister_old(self):
        self.file_system_state.add_old_mister_binary(self.installed_system_path)
        self.sut.queue_file(file_mister_descr(), FILE_MiSTer)
        self.sut.download_files(False)
        self.assertDownloaded([FILE_MiSTer], [FILE_MiSTer], need_reboot=True)
        self.assertEqual(hash_MiSTer, self.file_system.hash(FILE_MiSTer))
        self.assertEqual(hash_MiSTer_old, self.file_system.hash(FILE_MiSTer_old))
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (on_installed_system(FILE_MiSTer), on_installed_system(FILE_MiSTer_old))},
            {'scope': 'move', 'data': (on_installed_system(FILE_MiSTer_new), on_installed_system(FILE_MiSTer))},
        ]), self.file_system.write_records)

    def test_download_mister_file___from_scratch___stores_it_as_mister_and_mister_old_doesnt_exist(self):
        self.sut.queue_file(file_mister_descr(), FILE_MiSTer)
        self.sut.download_files(False)
        self.assertDownloaded([FILE_MiSTer], [FILE_MiSTer], need_reboot=True)
        self.assertEqual(hash_MiSTer, self.file_system.hash(FILE_MiSTer))
        self.assertFalse(self.file_system.is_file(FILE_MiSTer_old))
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (on_installed_system(FILE_MiSTer_new), on_installed_system(FILE_MiSTer))},
        ]), self.file_system.write_records)

    def assertDownloaded(self, oks, run=None, errors=None, need_reboot=False):
        self.assertEqual(oks, self.sut.correctly_downloaded_files())
        self.assertEqual(errors if errors is not None else [], self.sut.errors())
        self.assertEqual(run if run is not None else [], self.sut.run_files())
        self.assertEqual(need_reboot, self.sut.needs_reboot())

    def download_one(self):
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_one, 'size': 1}, file_one)
        self.sut.download_files(False)

    def download_big_file(self, hash_value):
        self.sut.queue_file({'url': 'https://fake.com/huge', 'hash': hash_value, 'size': big_size}, file_big)
        self.sut.download_files(False)

    def download_reboot(self):
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_menu_rbf, 'reboot': True, 'path': 'system', 'size': 23}, file_menu_rbf)
        self.sut.download_files(False)
