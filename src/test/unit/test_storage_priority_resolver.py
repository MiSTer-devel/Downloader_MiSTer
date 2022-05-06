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
from pathlib import Path

from downloader.config import default_config
from downloader.constants import K_BASE_PATH, K_STORAGE_PRIORITY, PathType, MEDIA_FAT_CIFS, MEDIA_FAT, MEDIA_USB2, \
    MEDIA_USB5, MEDIA_USB0, MEDIA_USB4, MEDIA_USB1, MEDIA_USB3
from downloader.storage_priority_resolver import StoragePriorityError
from test.objects import path_with
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_storage_priority_resolver import StoragePriorityResolverFactory


games = 'games'
games_cons = 'games/cons'
games_cons_file_a = 'games/cons/file_a'

media_usb0_games_cons = path_with(MEDIA_USB0, games_cons)
media_usb2_games_cons = path_with(MEDIA_USB2, games_cons)
media_usb5_games_cons = path_with(MEDIA_USB5, games_cons)
media_fat_cifs_games_cons = path_with(MEDIA_FAT_CIFS, games_cons)
media_fat_cifs_games = path_with(MEDIA_FAT_CIFS, games)


def config_storage_priority_prefer_media_usb0():
    return {K_STORAGE_PRIORITY: 'prefer_sd', K_BASE_PATH: MEDIA_USB0}


def config_storage_priority_prefer_media_fat():
    return {K_STORAGE_PRIORITY: 'prefer_sd', K_BASE_PATH: MEDIA_FAT}


def config_storage_priority_prefer_external_with_base_path_media_fat():
    return {K_STORAGE_PRIORITY: 'prefer_external', K_BASE_PATH: MEDIA_FAT}


def fs_external_drives():
    return fs([MEDIA_USB3, MEDIA_USB1, MEDIA_USB0, MEDIA_USB2, MEDIA_USB4, MEDIA_FAT_CIFS])


class TestStoragePriorityResolver(unittest.TestCase):

    def test_translate_correct_paths(self):
        for n, (expected, config, file_system) in enumerate([
            (MEDIA_FAT, {K_STORAGE_PRIORITY: 'off', K_BASE_PATH: MEDIA_FAT}, None),
            (MEDIA_FAT, {K_STORAGE_PRIORITY: 'off', K_BASE_PATH: MEDIA_FAT}, fs([])),
            (MEDIA_USB4, {K_STORAGE_PRIORITY: MEDIA_USB4}, fs([MEDIA_USB4])),
            (MEDIA_USB0, config_storage_priority_prefer_media_usb0(), fs([])),
            (MEDIA_USB0, config_storage_priority_prefer_media_usb0(), fs([media_usb0_games_cons])),
            (MEDIA_USB2, config_storage_priority_prefer_media_usb0(), fs([media_usb5_games_cons, media_usb2_games_cons])),
            (MEDIA_USB5, config_storage_priority_prefer_media_usb0(), fs([media_usb5_games_cons, media_fat_cifs_games_cons])),
            (MEDIA_FAT_CIFS, config_storage_priority_prefer_media_fat(), fs([media_fat_cifs_games_cons])),
            (MEDIA_FAT, config_storage_priority_prefer_media_fat(), fs([media_fat_cifs_games])),
            (MEDIA_FAT_CIFS, config_storage_priority_prefer_external_with_base_path_media_fat(), fs([media_fat_cifs_games_cons])),
            (MEDIA_FAT_CIFS, config_storage_priority_prefer_external_with_base_path_media_fat(), fs([media_fat_cifs_games])),
            (MEDIA_FAT_CIFS, config_storage_priority_prefer_external_with_base_path_media_fat(), fs([MEDIA_FAT_CIFS])),
            (MEDIA_FAT, config_storage_priority_prefer_external_with_base_path_media_fat(), fs([])),
            (MEDIA_USB0, config_storage_priority_prefer_external_with_base_path_media_fat(), fs_external_drives()),
            (MEDIA_FAT, config_storage_priority_prefer_media_fat(), fs_external_drives()),
        ]):
            with self.subTest('%s: %s' % (n + 1, expected)):
                self.assert_translated_path(expected, games_cons_file_a, config, file_system)

    def test_translate_wrong_paths___raises_error(self):
        for path, path_type in [
            ('games/yasta', PathType.FILE),
            ('|games/cons/file_a', PathType.FILE),
            ('|games', PathType.FOLDER),
        ]:
            with self.subTest(path):
                self.assertRaises(StoragePriorityError, lambda: StoragePriorityResolverFactory().create(default_config(), {}).resolve_storage_priority(path, path_type))

    def assert_translated_path(self, expected, path, config=None, file_system_factory=None):
        sut = StoragePriorityResolverFactory(file_system_factory=file_system_factory).create(config, {})
        self.assertEqual(expected, sut.resolve_storage_priority(path, PathType.FILE))


def fs(input_folders):
    state = FileSystemState()
    for folder in input_folders:
        state.add_full_folder_path(str(Path(folder).parent))
        state.add_full_folder_path(folder)

    return FileSystemFactory(state=state)
