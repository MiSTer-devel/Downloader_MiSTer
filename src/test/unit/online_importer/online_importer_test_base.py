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

from test.fake_file_system_factory import fs_data
from test.fake_online_importer import OnlineImporter
from test.objects import remove_all_priority_paths, db_reboot_descr, empty_test_store


class OnlineImporterTestBase(unittest.TestCase):
    def assertReportsNothing(self, sut, save=False, failed_folders=None, failed_zips=None):
        self.assertReports(sut, [], save=save, failed_folders=failed_folders, failed_zips=failed_zips)

    def assertReports(self, sut, installed=None, errors=None, needs_reboot=False, save=True, failed_folders=None, failed_zips=None, full_partitions=None, validated=None, downloaded=None):
        box = sut.box()
        if installed is None and validated is None and downloaded is None:
            installed = []
        if errors is None:
            errors = []
        if failed_folders is None:
            failed_folders = []
        if failed_zips is None:
            failed_zips = []
        if full_partitions is None:
            full_partitions = []
        if downloaded is not None:
            self.assertEqual(sorted(remove_all_priority_paths(downloaded)), sorted(box.downloaded_files()), 'downloaded')
        if validated is not None:
            self.assertEqual(sorted(remove_all_priority_paths(validated)), sorted(box.present_validated_files()), 'validated')
        if installed is not None:
            self.assertEqual(sorted(remove_all_priority_paths(installed)), sorted(box.installed_file_names()), 'installed')
        self.assertEqual(sorted(remove_all_priority_paths(errors)), sorted(box.failed_files()), 'errors')
        self.assertEqual(needs_reboot, sut.needs_reboot(), 'needs reboot')
        self.assertEqual(sorted(remove_all_priority_paths(failed_folders)), sorted(sut.folders_that_failed()), 'failed folders')
        self.assertEqual(sorted(remove_all_priority_paths(failed_zips)), sorted(sut.zips_that_failed()), 'failed zips')
        self.assertEqual(sorted(full_partitions), sorted(sut.full_partitions()), 'full partitions')
        self.assertEqual(save, sut.needs_save, 'needs save')

    def assertEverythingIsClean(self, sut, store, save=False):
        self.assertEqual(empty_test_store(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReportsNothing(sut, save=save)

    def _download_db(self, db, store, inputs):
        return OnlineImporter\
            .from_implicit_inputs(inputs)\
            .add_db(db, store)\
            .download(False)

    def _download_databases(self, fs_inputs, dbs, input_stores=None, free_space_reservation=None):
        sut = OnlineImporter.from_implicit_inputs(fs_inputs, free_space_reservation=free_space_reservation)

        stores = input_stores or [empty_test_store() for _ in dbs]
        for db, store in zip(dbs, stores):
            sut.add_db(db, store)

        sut.download(False)

        return sut, stores

    def download_reboot_file(self, store, inputs):
        return self._download_db(db_reboot_descr(), store, inputs)

    def assertSystem(self, expected, sut, stores, free=None):
        self.assertEqual(expected["fs"], sut.fs_data)
        self.assertEqual(expected["stores"], stores)
        self.assertReports(sut,
                           installed=expected.get("ok", []),
                           errors=expected.get("errors", []),
                           full_partitions=expected.get("full_partitions", []),
                           save=expected.get("save", True),)
        if free is not None or "free" in expected: self.assertEqual(expected["free"], free)
