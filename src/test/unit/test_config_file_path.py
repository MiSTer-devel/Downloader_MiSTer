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
        self.assertEqual('/media/fat/downloader.ini', config_file_path(None))

    def test_config_file_path___with_simple_relative_str___returns_str_ini(self):
        self.assertEqual('./str.ini', config_file_path('str.sh'))

    def test_config_file_path___with_complex_relative_str___returns_str_ini(self):
        self.assertEqual('str/complex.ini', config_file_path('str/complex.sh'))

    def test_config_file_path___with_long_custom_path___returns_downloader_ini(self):
        self.assertEqual('/media/fat/custom/custom.ini', config_file_path('/media/fat/custom/custom.sh'))

    def test_config_file_path___with_long_scripts_path___returns_downloader_ini(self):
        self.assertEqual('/media/fat/script.ini', config_file_path('/media/fat/Scripts/script.sh'))
