# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.constants import file_MiSTer, file_MiSTer_new
from test.fake_file_downloader import FileDownloader
from test.objects import file_menu_rbf, hash_menu_rbf, file_one, hash_one, hash_MiSTer


class TestFileDownloader(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = FileDownloader()

    def test_download_nothing___from_scratch_no_issues___nothing_downloaded_no_errors(self):
        self.sut.download_files(False)
        self.assertDownloaded([])

    def test_download_files_one___from_scratch_no_issues___returns_correctly_downloaded_one_and_no_errors(self):
        self.download_one()
        self.assertDownloaded([file_one], [file_one])

    def test_download_files_one___from_scratch_with_retry___returns_correctly_downloaded_one_and_no_errors(self):
        self.sut.test_data.errors_at(file_one, 2)
        self.download_one()
        self.assertDownloaded([file_one], [file_one, file_one])

    def test_download_files_one___from_scratch_could_not_download___return_errors(self):
        self.sut.test_data.errors_at(file_one)
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_files_one___from_scratch_no_matching_hash___return_errors(self):
        self.sut.test_data.brings_file(file_one, {'hash': 'wrong'})
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_files_one___from_scratch_no_file_exists___return_errors(self):
        self.sut.test_data.misses_file(file_one)
        self.download_one()
        self.assertDownloaded([], run=[file_one, file_one, file_one, file_one], errors=[file_one])

    def test_download_reboot_file___from_scratch_no_issues___needs_reboot(self):
        self.download_reboot()
        self.assertDownloaded([file_menu_rbf], [file_menu_rbf], need_reboot=True)

    def test_download_reboot_file___update_no_issues___needs_reboot(self):
        self.sut.file_system.test_data.with_file(file_menu_rbf, {'hash': 'old'})
        self.download_reboot()
        self.assertDownloaded([file_menu_rbf], [file_menu_rbf], need_reboot=True)

    def test_download_reboot_file___no_changes_no_issues___no_need_to_reboot(self):
        self.sut.file_system.test_data.with_file(file_menu_rbf, {'hash': hash_menu_rbf})
        self.download_reboot()
        self.assertDownloaded([file_menu_rbf])

    def test_download_mister_file___from_scratch_no_issues___stores_it_as_mister(self):
        self.sut.file_system.test_data.with_old_mister_binary()
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_MiSTer, 'reboot': True, 'path': 'system'}, file_MiSTer)
        self.sut.download_files(False)
        self.assertDownloaded([file_MiSTer], [file_MiSTer], need_reboot=True)
        self.assertTrue(self.sut.file_system.is_file(file_MiSTer))

    def test_download_mister_file___from_scratch_no_issues___adds_the_three_mister_files_on_system_paths(self):
        self.sut.file_system.test_data.with_old_mister_binary()
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_MiSTer, 'reboot': True, 'path': 'system'}, file_MiSTer)
        self.sut.download_files(False)
        self.assertEqual([file_MiSTer, file_MiSTer_new, self.sut.local_repository.old_mister_path], self.sut.file_system.system_paths)

    def assertDownloaded(self, oks, run=None, errors=None, need_reboot=False):
        self.assertEqual(oks, self.sut.correctly_downloaded_files())
        self.assertEqual(errors if errors is not None else [], self.sut.errors())
        self.assertEqual(run if run is not None else [], self.sut.run_files())
        self.assertEqual(need_reboot, self.sut.needs_reboot())

    def download_one(self):
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_one}, file_one)
        self.sut.download_files(False)

    def download_reboot(self):
        self.sut.queue_file({'url': 'https://fake.com/bar', 'hash': hash_menu_rbf, 'reboot': True, 'path': 'system'}, file_menu_rbf)
        self.sut.download_files(False)
