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

from downloader.config import default_config
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.objects_old_pext import db_test_descr, folder_games_nes, store_descr, empty_test_store, zip_desc, \
    zipped_nes_palettes_id, fix_old_pext_store
from test.zip_objects_old_pext import files_nes_palettes, folders_games_nes_palettes, with_installed_nes_palettes_on_fs, \
    zipped_nes_palettes_desc, cheats_folder_zip_desc, summary_json_from_cheats_folder, zipped_files_from_cheats_folder, cheats_folder_id, cheats_folder_folders, \
    cheats_folder_files, with_installed_cheats_folder_on_fs
from test.fake_online_importer import OnlineImporter
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase

# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithZipsOldPext(OnlineImporterTestBase):

    def setUp(self) -> None:
        self.config = default_config()
        self.implicit_inputs = ImporterImplicitInputs(config=self.config)
        self.sut = OnlineImporter.from_implicit_inputs(self.implicit_inputs)

    def download(self, db, store):
        self.sut.add_db(db, store)
        self.sut.download(False)
        return store

    def test_download_two_zips_in_one_db___on_empty_store__installs_both_zips_in_the_store_and_reports_them(self):
        self.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents

        store = self.download(db_test_descr(zips={
            zipped_nes_palettes_id: zipped_nes_palettes_desc(url=False),
            cheats_folder_id: cheats_folder_zip_desc(zipped_files=zipped_files_from_cheats_folder(), summary=summary_json_from_cheats_folder()),
        }), empty_test_store())

        self.assertEqual(fix_old_pext_store(store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/'),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        )), store)
        self.assertSutReports([*cheats_folder_files(), *files_nes_palettes()])

    def test_download_two_zips_in_one_db___on_a_store_with_the_same_db_previously_installed__changes_nothing(self):
        with_installed_cheats_folder_on_fs(self.implicit_inputs.file_system_state)
        with_installed_nes_palettes_on_fs(self.implicit_inputs.file_system_state)

        self.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents

        store = self.download(db_test_descr(zips={
            zipped_nes_palettes_id: zipped_nes_palettes_desc(url=False),
            cheats_folder_id: cheats_folder_zip_desc(zipped_files=zipped_files_from_cheats_folder(), summary=summary_json_from_cheats_folder()),
        }), store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/'),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        ))

        self.assertEqual(fix_old_pext_store(store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/'),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        )), store)

        self.assertSutReports([], save=True)

    def assertSutReports(self, installed, errors=None, needs_reboot=False, save=True):
        return self.assertReports(self.sut, installed, errors, needs_reboot, save)


