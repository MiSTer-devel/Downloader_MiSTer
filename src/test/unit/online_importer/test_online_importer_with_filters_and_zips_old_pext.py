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
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.fake_online_importer import OnlineImporter
from test.objects_old_pext import db_test_descr, store_descr, empty_test_store, folder_games, folder_games_nes, \
    file_nes_palette_a, fix_old_pext_store
from test.zip_objects_old_pext import file_nes_palette_a_descr_zipped, zipped_nes_palettes_desc, zipped_nes_palettes_id, folder_games_nes_palettes


# @TODO: Remove this file when support for the old pext syntax '|' is removed
class TestOnlineImporterWithFiltersAndZipsOldPext(unittest.TestCase):
    def test_download_zipped_nes_palettes_folder___with_empty_store_and_negative_nes_filter___installs_filtered_nes_zip_data_and_nothing_in_fs(self):
        actual_store = self.download_zipped_nes_palettes_folder(empty_test_store(), '!nes')
        self.assertEqual(fix_old_pext_store(store_with_filtered_nes_palette_zip_data()), actual_store)
        self.assertNothingInstalled()

    def test_download_zipped_nes_palettes_folder___with_store_with_filtered_nes_palette_zip_data_and_no_filter___installs_nes_zip_data_and_palette_file(self):
        actual_store = self.download_zipped_nes_palettes_folder(store_with_filtered_nes_palette_zip_data(), '')
        self.assertEqual(fix_old_pext_store(store_with_nes_palette_zip()), actual_store)
        self.assertNesPaletteIsInstalled()

    def test_download_zipped_nes_palettes_folder___with_store_with_nes_palette_zip_and_negative_nes_filter___installs_filtered_nes_zip_data_and_nothing_in_fs(self):
        actual_store = self.download_zipped_nes_palettes_folder(store_with_nes_palette_zip(), '!nes')
        self.assertEqual(fix_old_pext_store(store_with_filtered_nes_palette_zip_data()), actual_store)
        self.assertNothingInstalled()

    def download_zipped_nes_palettes_folder(self, store, filter_value, implicit_inputs=None):
        implicit_inputs = implicit_inputs if implicit_inputs is not None else ImporterImplicitInputs()
        implicit_inputs.config[K_FILTER] = filter_value
        implicit_inputs.config[K_ZIP_FILE_COUNT_THRESHOLD] = 0 # This will cause to unzip the contents

        self.sut = OnlineImporter.from_implicit_inputs(implicit_inputs)

        self.sut.add_db(db_test_descr(zips={
            zipped_nes_palettes_id: zipped_nes_palettes_desc(url=False, tags=True)
        }), store).download(False)

        return store

    def assertNesPaletteIsInstalled(self):
        self.assertEqual(fs_data(
            files={file_nes_palette_a: file_nes_palette_a_descr_zipped()},
            folders=[folder_games, folder_games_nes, folder_games_nes_palettes]
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
        files={file_nes_palette_a[1:]: file_nes_palette_a_descr_zipped(tags=True, url=False)},
        folders={
            folder_games[1:]: {"zip_id": zipped_nes_palettes_id, "tags": ["games"]},
            folder_games_nes[1:]: {"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes"]},
            folder_games_nes_palettes[1:]: {"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes", "palette"]},
        }
    )
