# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from downloader.config import config_file_path


class TestConfigFilePath(unittest.TestCase):

    def test_config_file_path___with_none___returns_downloader_ini(self):
        self.assertEqual('/media/fat/downloader.ini', config_file_path(env(launcher_path=None), None))

    def test_config_file_path___with_simple_relative_str_and_working_dir_at_fat___returns_media_fat_str_ini(self):
        self.assertEqual('/media/fat/str.ini', config_file_path(env(launcher_path='str.sh'), '/media/fat'))

    def test_config_file_path___with_complex_relative_str___returns_str_ini(self):
        self.assertEqual('./str/complex.ini', config_file_path(env(launcher_path='str/complex.sh'), None))

    def test_config_file_path___with_long_custom_path___returns_long_custom_ini(self):
        self.assertEqual('/media/fat/custom/custom.ini', config_file_path(env(launcher_path='/media/fat/custom/custom.sh'), None))

    def test_config_file_path___with_long_scripts_path___returns_downloader_ini(self):
        self.assertEqual('/media/fat/script.ini', config_file_path(env(launcher_path='/media/fat/Scripts/script.sh'), None))

    def test_config_file_path___with_relative_scripts_path___returns_relative_downloader_ini_without_scripts(self):
        self.assertEqual('./downloader.ini', config_file_path(env(launcher_path='./Scripts/downloader.sh'), None))

    def test_config_file_path___with_simple_relative_str_and_working_dir_at_scripts___returns_downloader_ini(self):
        self.assertEqual('/media/fat/downloader.ini', config_file_path(env(launcher_path='./downloader.sh'), '/media/fat/Scripts'))

    def test_config_file_path___with_relative_media_fat_scripts_path___returns_relative_downloader_ini_without_scripts(self):
        self.assertEqual('./media/fat/downloader.ini', config_file_path(env(launcher_path='./media/fat/Scripts/downloader.sh'), None))

    def test_config_file_path___from_ini_path___returns_ini_path(self):
        self.assertEqual('/media/fat/script.ini', config_file_path(env(launcher_path='/media/fat/Scripts/whatever.sh', ini_path='/media/fat/script.ini'), None))


def env(launcher_path, ini_path=None):
    return {
        'DOWNLOADER_LAUNCHER_PATH': launcher_path,
        'DOWNLOADER_INI_PATH': ini_path,
    }
