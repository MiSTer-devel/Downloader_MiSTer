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
import shutil
import os
import os.path
from pathlib import Path
from downloader.config import ConfigReader
from downloader.constants import file_mister_downloader_needs_reboot
from test.objects import debug_env, default_base_path
from test.fake_logger import NoLogger
import subprocess


class TestSmallDbInstall(unittest.TestCase):

    def setUp(self) -> None:
        try:
            Path(file_mister_downloader_needs_reboot).unlink()
        except FileNotFoundError as _:
            pass

    def test_small_db_1(self):
        print('test_small_db_1')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_1.ini")
        self.assertTrue(os.path.isfile(file_mister_downloader_needs_reboot))

    def test_small_db_2(self):
        print('test_small_db_2')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_2.ini")
        self.assertFalse(os.path.isfile(file_mister_downloader_needs_reboot))

    def test_small_db_3(self):
        print('test_small_db_3')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_3.ini")
        self.assertFalse(os.path.isfile(file_mister_downloader_needs_reboot))

    def assertRunOk(self, ini_path):
        config = ConfigReader(NoLogger(), debug_env()).read_config(ini_path)
        shutil.rmtree(config['base_path'], ignore_errors=True)
        shutil.rmtree(config['base_system_path'], ignore_errors=True)
        mister_path = Path('%s/MiSTer' % config['base_system_path'])
        os.makedirs(str(mister_path.parent), exist_ok=True)
        mister_path.touch()
        tool = str(Path(ini_path).with_suffix('.sh'))
        subprocess.run('cd ..; ./src/build.sh > src/%s' % tool, shell=True, stderr=subprocess.STDOUT)
        subprocess.run(['chmod', '+x', tool], shell=False, stderr=subprocess.STDOUT)
        test_env = os.environ.copy()
        test_env['CURL_SSL'] = ''
        test_env['DEBUG'] = 'true'
        test_env['FAIL_ON_FILE_ERROR'] = 'true'
        test_env['DEFAULT_BASE_PATH'] = default_base_path
        result = subprocess.run([tool], stderr=subprocess.STDOUT, env=test_env)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isfile("%s/Scripts/.config/downloader/downloader.json.zip" % config['base_system_path']))
        os.unlink(tool)
