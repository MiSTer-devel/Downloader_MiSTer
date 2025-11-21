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

import unittest
from downloader.constants import K_ZIP_FILE_COUNT_THRESHOLD, K_FILTER
from test.objects import empty_test_store, store_descr, zipped_nes_palettes_id, folder_games, file_nes_palette_a, \
    folder_games_nes_palettes, folder_games_nes
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.fake_online_importer import OnlineImporter
from test.objects_old_pext import db_test_descr as db_test_descr_old_pext, \
    folder_games as folder_games_old_pext, folder_games_nes as folder_games_nes_old_pext, \
    file_nes_palette_a as file_nes_palette_a_old_pext
from test.zip_objects_old_pext import file_nes_palette_a_descr_zipped as file_nes_palette_a_descr_zipped_old_pext, \
    zipped_nes_palettes_desc as zipped_nes_palettes_desc_old_pext, \
    zipped_nes_palettes_id as zipped_nes_palettes_id_old_pext, \
    folder_games_nes_palettes as folder_games_nes_palettes_old_pext
from test.zip_objects import zipped_nes_palettes_desc, file_nes_palette_a_descr_zipped


# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithFiltersAndZipsOldPext(unittest.TestCase):
    def test_download_zipped_nes_palettes_folder___with_empty_store_and_negative_nes_filter___installs_filtered_nes_zip_data_and_nothing_in_fs(self):
        actual_store = self.download_zipped_nes_palettes_folder(empty_test_store(), '!nes')
        self.assertEqual(store_with_filtered_nes_palette_zip_data(), actual_store)
        self.assertNothingInstalled()

    def test_download_zipped_nes_palettes_folder___with_store_with_filtered_nes_palette_zip_data_and_no_filter___installs_nes_zip_data_and_palette_file(self):
        actual_store = self.download_zipped_nes_palettes_folder(store_with_filtered_nes_palette_zip_data(), '')
        self.assertEqual(store_with_nes_palette_zip(), actual_store)
        self.assertNesPaletteIsInstalled()

    def test_download_zipped_nes_palettes_folder___with_store_with_nes_palette_zip_and_negative_nes_filter___installs_filtered_nes_zip_data_and_nothing_in_fs(self):
        actual_store = self.download_zipped_nes_palettes_folder(store_with_nes_palette_zip(), '!nes')
        self.assertEqual(store_with_filtered_nes_palette_zip_data(), actual_store)
        self.assertNothingInstalled()

    def download_zipped_nes_palettes_folder(self, store, filter_value, implicit_inputs=None):
        implicit_inputs = implicit_inputs if implicit_inputs is not None else ImporterImplicitInputs()
        implicit_inputs.config[K_FILTER] = filter_value
        implicit_inputs.config[K_ZIP_FILE_COUNT_THRESHOLD] = 0 # This will cause to unzip the contents

        self.sut = OnlineImporter.from_implicit_inputs(implicit_inputs)

        self.sut.add_db(db_test_descr_old_pext(zips={
            zipped_nes_palettes_id_old_pext: zipped_nes_palettes_desc_old_pext(url=False, tags=True)
        }), store).download()

        return store

    def assertNesPaletteIsInstalled(self):
        self.assertEqual(fs_data(
            files={file_nes_palette_a_old_pext: file_nes_palette_a_descr_zipped_old_pext()},
            folders=[folder_games_old_pext, folder_games_nes_old_pext, folder_games_nes_palettes_old_pext]
        ), self.sut.fs_data)

    def assertNothingInstalled(self):
        self.assertEqual(fs_data(), self.sut.fs_data)

def store_with_filtered_nes_palette_zip_data():
    return store_descr(
        zips={
            zipped_nes_palettes_id: zipped_nes_palettes_desc(url=False, zipped_files=False, summary=False),
        },
        folders={folder_games: {"path": "pext", "zip_id": zipped_nes_palettes_id, "tags": ["games"]}},
        filtered_zip_data={
            zipped_nes_palettes_id: {
                "files": {file_nes_palette_a: file_nes_palette_a_descr_zipped(tags=True, url=False)},
                "folders": {
                    folder_games_nes_palettes: {"path": "pext", "zip_id": zipped_nes_palettes_id, "tags": ["games", "nes", "palette"]},
                    folder_games_nes: {"path": "pext", "zip_id": zipped_nes_palettes_id, "tags": ["games", "nes"]}
                }
            }
        }
    )


def store_with_nes_palette_zip():
    return store_descr(
        zips={
            zipped_nes_palettes_id: zipped_nes_palettes_desc(url=False, zipped_files=False, summary=False),
        },
        files={file_nes_palette_a: file_nes_palette_a_descr_zipped(tags=True, url=False)},
        folders={
            folder_games: {"zip_id": zipped_nes_palettes_id, "tags": ["games"], "path": "pext"},
            folder_games_nes: {"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes"], "path": "pext"},
            folder_games_nes_palettes: {"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes", "palette"], "path": "pext"},
        }
    )
