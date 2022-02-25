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

from downloader.constants import K_BASE_PATH, K_GAMESDIR_PATH
from downloader.gamesdir_resolver import GamesdirError
from test.fake_file_system_factory import FileSystemFactory
from test.fake_gamesdir_resolver import GamesdirResolver


def fs(input_folders):
    result = FileSystemFactory().create_for_system_scope()
    actual_folders = []
    for folder in input_folders:
        actual_folders.append(str(Path(folder).parent))
        actual_folders.append(folder)
    result.test_data.with_folders(actual_folders)
    return result


def gamesdir_config_media_fat():
    return {K_GAMESDIR_PATH: 'auto', K_BASE_PATH: '/media/usb0'}


class TestGamesdirResolver(unittest.TestCase):

    def test_translate_correct_paths(self):
        for n, (path, expected, config, file_system) in enumerate([
            ('games/cons/file_a', 'games/cons/file_a', None, None),
            ('|games/cons/file_a', '/media/fat/games/cons/file_a', {K_GAMESDIR_PATH: '/media/fat'}, None),
            ('|games/cons/file_a', 'games/cons/file_a', {K_GAMESDIR_PATH: 'auto'}, fs([])),
            ('|games/cons/file_a', '/media/usb0/games/cons/file_a', gamesdir_config_media_fat(), fs(['/media/usb0/games/cons'])),
            ('|games/cons/file_a', '/media/usb2/games/cons/file_a', gamesdir_config_media_fat(), fs(['/media/usb5/games/cons', '/media/usb2/games/cons'])),
            ('|games/cons/file_a', '/media/usb5/games/cons/file_a', gamesdir_config_media_fat(), fs(['/media/usb5/games/cons', '/media/fat/cifs/games/cons'])),
            ('|games/cons/file_a', '/media/fat/cifs/games/cons/file_a', gamesdir_config_media_fat(), fs(['/media/fat/cifs/games/cons'])),
            ('and/something/else', 'and/something/else', None, None),
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assert_translated_path(expected, path, config, file_system)

    def test_translate_wrong_paths___raises_error(self):
        for path in ['|other/random/file_a', '|games/yasta']:
            with self.subTest(path):
                self.assertRaises(GamesdirError, lambda: GamesdirResolver().translate_path(path))

    def assert_translated_path(self, expected, path, config=None, file_system=None):
        self.assertEqual(expected, GamesdirResolver(config=config, file_system=file_system).translate_path(path))

