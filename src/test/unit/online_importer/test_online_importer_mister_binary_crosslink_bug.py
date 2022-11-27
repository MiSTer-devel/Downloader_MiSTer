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
from downloader.constants import FILE_MiSTer_old, FILE_MiSTer, FILE_MiSTer_new, \
    DISTRIBUTION_MISTER_DB_ID, MEDIA_FAT, MEDIA_USB0, STORAGE_PRIORITY_PREFER_SD
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data, fs_records
from test.objects import db_distribution_mister, file_mister_descr, \
    store_descr, hash_MiSTer_old, remove_all_priority_paths, media_fat, config_with, file_mister_old_descr
from test.fake_online_importer import OnlineImporter


# See: https://github.com/MiSTer-devel/Downloader_MiSTer/issues/24
class TestOnlineImporterMiSTerBinaryCrosslinkBug(unittest.TestCase):

    def test_installing_new_main_on_top_of_old_one___moves_old_one_to_mister_old_location_on_same_directory_despite_base_path(self):
        config = config_with(
            base_path=MEDIA_USB0,
            base_system_path=MEDIA_FAT,
            storage_priority=STORAGE_PRIORITY_PREFER_SD
        )

        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(
            files={media_fat(FILE_MiSTer): {'hash': hash_MiSTer_old}},
            config=config
        ))
        store = store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_old_descr()}, base_path=MEDIA_USB0)

        sut.add_db(db_distribution_mister(files={FILE_MiSTer: file_mister_descr()}), store)
        sut.download(False)

        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr()}, base_path=MEDIA_USB0), store)
        self.assertEqual(fs_data(
            files={
                media_fat(FILE_MiSTer): file_mister_descr(),
                media_fat(FILE_MiSTer_old): {'hash': hash_MiSTer_old}
            },
        ), sut.fs_data)
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (media_fat(FILE_MiSTer), media_fat(FILE_MiSTer_old))},
            {'scope': 'move', 'data': (media_fat(FILE_MiSTer_new), media_fat(FILE_MiSTer))},
        ]), sut.fs_records)
        self.assertReports(sut, [FILE_MiSTer], needs_reboot=True)

    def assertReportsNothing(self, sut, save=False):
        self.assertReports(sut, [], save=save)

    def assertReports(self, sut, installed, errors=None, needs_reboot=False, save=True):
        if errors is None:
            errors = []
        self.assertEqual(remove_all_priority_paths(installed), sut.correctly_installed_files())
        self.assertEqual(remove_all_priority_paths(errors), sut.files_that_failed())
        self.assertEqual(needs_reboot, sut.needs_reboot())
        self.assertEqual(save, sut.needs_save)