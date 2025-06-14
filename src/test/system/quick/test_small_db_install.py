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
import shutil
import time
import os
import os.path
from pathlib import Path
from downloader.config_reader import ConfigReader
from downloader.constants import FILE_mister_downloader_needs_reboot, KENV_CURL_SSL, KENV_DEBUG, \
    KENV_FAIL_ON_FILE_ERROR, KENV_DEFAULT_BASE_PATH, KENV_DOWNLOADER_INI_PATH
from downloader.file_system import is_windows
from test.objects import debug_env
from test.fake_logger import NoLogger
import subprocess

from test.system.quick.sandbox_test_base import tmp_default_base_path


class TestSmallDbInstall(unittest.TestCase):

    def setUp(self) -> None:
        try:
            Path(FILE_mister_downloader_needs_reboot).unlink()
        except FileNotFoundError as _:
            pass

    def test_small_db_1(self):
        print('test_small_db_1')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_1.ini")
        self.assertTrue(os.path.isfile(FILE_mister_downloader_needs_reboot))

    def test_small_db_2(self):
        print('test_small_db_2')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_2.ini")
        self.assertFalse(os.path.isfile(FILE_mister_downloader_needs_reboot))

    def test_small_db_3(self):
        print('test_small_db_3')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_3.ini")
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_3.ini", save=False, from_scratch=False)
        self.assertFalse(os.path.isfile(FILE_mister_downloader_needs_reboot))

    def test_small_db_4(self):
        print('test_small_db_4')
        self.assertRunOk("test/system/fixtures/small_db_install/small_db_4_first_run.ini")
        self.assertTrue(os.path.isfile(f'{tmp_default_base_path}/_Cores/core.rbf'))

        self.assertRunOk("test/system/fixtures/small_db_install/small_db_4_second_run.ini")
        self.assertFalse(os.path.isfile(f'{tmp_default_base_path}/_Cores/core.rbf'))
        self.assertTrue(os.path.isfile('/tmp/special_base_path/_Cores/core.rbf'))

    def assertRunOk(self, ini_path, save=True, from_scratch=True):
        env = debug_env()
        env['DEFAULT_BASE_PATH'] = tmp_default_base_path
        config = ConfigReader(NoLogger(), env, time.monotonic()).read_config(ini_path)
        if from_scratch:
            shutil.rmtree(config['base_path'], ignore_errors=True)
            shutil.rmtree(config['base_system_path'], ignore_errors=True)
            mister_path = Path('%s/MiSTer' % config['base_system_path'])
            os.makedirs(str(mister_path.parent), exist_ok=True)
            mister_path.touch()

        store_path = Path("%s/Scripts/.config/downloader/downloader.json" % config['base_system_path'])
        mtime = 0 if not store_path.is_file() else store_path.stat().st_mtime

        test_env = os.environ.copy()
        test_env[KENV_CURL_SSL] = ''
        test_env[KENV_DEBUG] = 'true'
        test_env[KENV_FAIL_ON_FILE_ERROR] = 'true'
        test_env[KENV_DOWNLOADER_INI_PATH] = ini_path
        test_env[KENV_DEFAULT_BASE_PATH] = tmp_default_base_path

        if is_windows:
            result = subprocess.run(['python3', '__main__.py'], stderr=subprocess.STDOUT, env=test_env)
        else:
            tool = str(Path(ini_path).with_suffix('.sh'))
            subprocess.run('cd ..; ./src/build.sh > src/%s' % tool, shell=True, stderr=subprocess.STDOUT)
            subprocess.run(['chmod', '+x', tool], shell=False, stderr=subprocess.STDOUT)

            result = subprocess.run(tool, stderr=subprocess.STDOUT, env=test_env)
            shutil.rmtree('src/%s' % tool, ignore_errors=True)
            os.unlink(tool)

        self.assertEqual(result.returncode, 0)
        time.sleep(0.25)
        new_mtime = 0 if not store_path.is_file() else store_path.stat().st_mtime
        if save:
            self.assertNotEqual(mtime, new_mtime)
        else:
            self.assertEqual(mtime, new_mtime)
