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

from test.fake_online_importer import OnlineImporter
from test.objects import remove_all_priority_paths


class OnlineImporterTestBase(unittest.TestCase):
    def assertReportsNothing(self, sut, save=False, failed_folders=None, failed_zips=None):
        self.assertReports(sut, [], save=save, failed_folders=failed_folders, failed_zips=failed_zips)

    def assertReports(self, sut, installed, errors=None, needs_reboot=False, save=True, failed_folders=None, failed_zips=None):
        if errors is None:
            errors = []
        if failed_folders is None:
            failed_folders = []
        if failed_zips is None:
            failed_zips = []
        self.assertEqual(sorted(remove_all_priority_paths(installed)), sorted(sut.correctly_installed_files()))
        self.assertEqual(sorted(remove_all_priority_paths(errors)), sorted(sut.files_that_failed()))
        self.assertEqual(needs_reboot, sut.needs_reboot())
        self.assertEqual(sorted(remove_all_priority_paths(failed_folders)), sorted(sut.folders_that_failed()))
        self.assertEqual(sorted(remove_all_priority_paths(failed_zips)), sorted(sut.zips_that_failed()))
        self.assertEqual(save, sut.needs_save)

    def _download_db(self, db, store, inputs):
        return OnlineImporter\
            .from_implicit_inputs(inputs)\
            .add_db(db, store)\
            .download(False)
