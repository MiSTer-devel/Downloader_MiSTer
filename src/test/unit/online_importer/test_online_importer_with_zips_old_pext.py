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
from test.objects import store_descr, zipped_nes_palettes_id, zip_desc, folder_games_nes, empty_test_store
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.objects_old_pext import db_test_descr as db_test_descr_old_pext, zipped_nes_palettes_id as zipped_nes_palettes_id_old_pext
from test.zip_objects_old_pext import files_nes_palettes as files_nes_palettes_old_pext, with_installed_nes_palettes_on_fs as with_installed_nes_palettes_on_fs_old_pext, \
    zipped_nes_palettes_desc as zipped_nes_palettes_desc_old_pext, cheats_folder_zip_desc as cheats_folder_zip_desc_old_pext, \
    summary_json_from_cheats_folder as summary_json_from_cheats_folder_old_pext, zipped_files_from_cheats_folder as zipped_files_from_cheats_folder_old_pext, \
    cheats_folder_id as cheats_folder_id_old_pext, cheats_folder_files as cheats_folder_files_old_pext, with_installed_cheats_folder_on_fs as with_installed_cheats_folder_on_fs_old_pext
from test.fake_online_importer import OnlineImporter
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from test.zip_objects import cheats_folder_id, cheats_folder_zip_desc, cheats_folder_files, cheats_folder_folders, \
    files_nes_palettes, folders_games_nes_palettes


# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithZipsOldPext(OnlineImporterTestBase):

    def setUp(self) -> None:
        self.config = default_config()
        self.implicit_inputs = ImporterImplicitInputs(config=self.config)
        self.sut = OnlineImporter.from_implicit_inputs(self.implicit_inputs)

    def download(self, db, store):
        self.sut.add_db(db, store)
        self.sut.download()
        return store

    def test_download_two_zips_in_one_db___on_empty_store__installs_both_zips_in_the_store_and_reports_them(self):
        self.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents

        store = self.download(db_test_descr_old_pext(zips={
            zipped_nes_palettes_id_old_pext: zipped_nes_palettes_desc_old_pext(url=False),
            cheats_folder_id_old_pext: cheats_folder_zip_desc_old_pext(zipped_files=zipped_files_from_cheats_folder_old_pext(), summary=summary_json_from_cheats_folder_old_pext()),
        }), empty_test_store())

        self.assertEqual(store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/', is_pext=True),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        ), store)
        self.assertSutReports([*cheats_folder_files_old_pext(), *files_nes_palettes_old_pext()])

    def test_download_two_zips_in_one_db___on_a_store_with_the_same_db_previously_installed__changes_nothing(self):
        with_installed_cheats_folder_on_fs_old_pext(self.implicit_inputs.file_system_state)
        with_installed_nes_palettes_on_fs_old_pext(self.implicit_inputs.file_system_state)

        self.config['zip_file_count_threshold'] = 0  # This will cause to unzip the contents

        store = self.download(db_test_descr_old_pext(zips={
            zipped_nes_palettes_id_old_pext: zipped_nes_palettes_desc_old_pext(url=False),
            cheats_folder_id_old_pext: cheats_folder_zip_desc_old_pext(zipped_files=zipped_files_from_cheats_folder_old_pext(), summary=summary_json_from_cheats_folder_old_pext()),
        }), store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/', is_pext=True),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        ))

        self.assertEqual(store_descr(
            zips={
                zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes + '/', is_pext=True),
                cheats_folder_id: cheats_folder_zip_desc()
            },
            files={**cheats_folder_files(url=False), **files_nes_palettes(url=False)},
            folders={**cheats_folder_folders(), **folders_games_nes_palettes()}
        ), store)

        self.assertSutReports([], save=False)

    def assertSutReports(self, installed, errors=None, needs_reboot=False, save=True):
        return self.assertReports(self.sut, installed, errors, needs_reboot, save)
