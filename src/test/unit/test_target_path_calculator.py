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
from pathlib import Path
import unittest

from downloader.config import default_config
from downloader.path_package import PathType
from downloader.constants import K_BASE_PATH, K_STORAGE_PRIORITY, MEDIA_FAT_CIFS, MEDIA_FAT, MEDIA_USB2, \
    MEDIA_USB5, MEDIA_USB0, MEDIA_USB4, MEDIA_USB1, MEDIA_USB3, STORAGE_PRIORITY_PREFER_SD, \
    STORAGE_PRIORITY_PREFER_EXTERNAL
from downloader.target_path_calculator import StoragePriorityError
from test.fake_file_system_factory import FileSystemFactory
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_target_path_calculator import TargetPathCalculatorFactory
from test.objects import config_with, path_with


base_path = '/standard'
base_system_path = '/system'
external_storage = 'off'


tmp_whatever = '/tmp/whatever'
normal_path_1 = 'normal/file'
normal_path_2 = 'other/file'

storage_priority_normal_path = '|games/core/file'

games = 'games'
games_cons = 'games/cons'
games_cons_file_a = '|games/cons/file_a'

media_usb0_games_cons = path_with(MEDIA_USB0, games_cons)
media_usb2_games_cons = path_with(MEDIA_USB2, games_cons)
media_usb5_games_cons = path_with(MEDIA_USB5, games_cons)
media_fat_cifs_games_cons = path_with(MEDIA_FAT_CIFS, games_cons)
media_fat_cifs_games = path_with(MEDIA_FAT_CIFS, games)


def config___prefer_sd___media_usb0():
    return {K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_SD, K_BASE_PATH: MEDIA_USB0}


def config___prefer_sd___media_fat():
    return {K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_SD, K_BASE_PATH: MEDIA_FAT}


def config___prefer_external___media_fat():
    return {K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_EXTERNAL, K_BASE_PATH: MEDIA_FAT}


def fs_external_drives():
    return fs([MEDIA_USB3, MEDIA_USB1, MEDIA_USB0, MEDIA_USB2, MEDIA_USB4, MEDIA_FAT_CIFS])

def sut():
    config=config_with(base_path=base_path, base_system_path=base_system_path, storage_priority=external_storage)
    return TargetPathCalculatorFactory(config=config).target_paths_calculator(config=config)


class TestTargetPathCalculator(unittest.TestCase):
    def test_resolve_correct_paths___return_expected_base_paths(self):
        for n, (path, expected) in enumerate([
            (normal_path_1, base_path),
            (normal_path_2, base_path),
            (tmp_whatever, None)
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assertEqual(expected, sut().deduce_target_path(path, {}, PathType.FILE)[0].drive)

    def test_resolve_correct_system_paths___return_expected_base_paths(self):
        for n, (path, expected, system_paths) in enumerate([
            (normal_path_1, base_path, []),
            (normal_path_1, base_system_path, [normal_path_1]),
            (tmp_whatever, None, [tmp_whatever])
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assert_system_resolve(expected, path, system_paths)

    def test_resolve_storage_priorities(self):
        self.assertEqual(base_path, sut().deduce_target_path(storage_priority_normal_path, {}, PathType.FILE)[0].drive)

    def test_translate_correct_paths(self):
        for n, (expected, config, file_system) in enumerate([
            (MEDIA_FAT, {K_STORAGE_PRIORITY: 'off', K_BASE_PATH: MEDIA_FAT}, None),
            (MEDIA_FAT, {K_STORAGE_PRIORITY: 'off', K_BASE_PATH: MEDIA_FAT}, fs([])),
            (MEDIA_USB0, config___prefer_sd___media_usb0(), fs([])),
            (MEDIA_USB0, config___prefer_sd___media_usb0(), fs([media_usb0_games_cons])),
            (MEDIA_USB2, config___prefer_sd___media_usb0(), fs([media_usb5_games_cons, media_usb2_games_cons])),
            (MEDIA_USB5, config___prefer_sd___media_usb0(), fs([media_usb5_games_cons, media_fat_cifs_games_cons])),
            (MEDIA_FAT_CIFS, config___prefer_sd___media_fat(), fs([media_fat_cifs_games_cons])),
            (MEDIA_FAT, config___prefer_sd___media_fat(), fs([media_fat_cifs_games])),
            (MEDIA_FAT_CIFS, config___prefer_external___media_fat(), fs([media_fat_cifs_games_cons])),
            (MEDIA_FAT_CIFS, config___prefer_external___media_fat(), fs([media_fat_cifs_games])),
            (MEDIA_FAT_CIFS, config___prefer_external___media_fat(), fs([MEDIA_FAT_CIFS])),
            (MEDIA_FAT, config___prefer_external___media_fat(), fs([])),
            (MEDIA_USB4, config___prefer_external___media_fat(), fs([MEDIA_USB4])),
            (MEDIA_USB0, config___prefer_external___media_fat(), fs_external_drives()),
            (MEDIA_FAT, config___prefer_sd___media_fat(), fs_external_drives()),
        ]):
            with self.subTest('%s: %s' % (n + 1, expected)):
                self.assert_translated_path(expected, games_cons_file_a, config, file_system)

    def test_translate_wrong_paths___raises_error(self):
        for path, path_type in [
            ('|games/yasta', PathType.FILE),
            ('|yasta', PathType.FILE),
        ]:
            with self.subTest(path):
                _, e = sut().deduce_target_path(path, {}, path_type)
                self.assertIsInstance(e, StoragePriorityError)

    def assert_translated_path(self, expected, path, config=None, file_system_factory: FileSystemFactory=None):
        file_system_factory = file_system_factory or FileSystemFactory()
        config = config or default_config()
        sut = TargetPathCalculatorFactory(file_system=file_system_factory.create_for_config(config)).target_paths_calculator(config=config)
        actual, e = sut.deduce_target_path(path, {}, PathType.FILE)
        if e is not None:
            raise e
        self.assertEqual(expected, actual.drive)

    def assert_system_resolve(self, expected, input, system_paths):
        this_sut = sut()
        description = {}
        for input in system_paths:
            description['path'] = 'system'
        self.assertEqual(expected, this_sut.deduce_target_path(input, description, PathType.FILE)[0].drive)


def fs(input_folders):
    state = FileSystemState()
    for folder in input_folders:
        path = Path(folder)
        for parent in path.parents:
            state.add_full_folder_path(str(parent))
        state.add_full_folder_path(folder)

    return FileSystemFactory(state=state)
