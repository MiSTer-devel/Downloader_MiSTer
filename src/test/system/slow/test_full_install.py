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
import shutil
import os
import os.path
from pathlib import Path
from downloader.config import ConfigReader
from downloader.constants import K_BASE_PATH, K_BASE_SYSTEM_PATH, KENV_CURL_SSL, KENV_DEBUG
from test.objects import debug_env
from test.fake_logger import NoLogger
from downloader.file_system import hash_file
import subprocess


class TestFullInstall(unittest.TestCase):

    def test_full_install_parallel(self):
        print('test_full_install_parallel')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")

    def test_full_install_and_rerun(self):
        print('test_full_install_and_rerun A)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")

        print('test_full_install_and_rerun B)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")
        self.assertTrue(os.path.isfile('/tmp/delme_parallel/MiSTer'))

    def test_full_install_remove_local_store_and_rerun(self):
        print('test_full_install_remove_local_store_and_rerun A)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")

        os.unlink('/tmp/delme_parallel/Scripts/.config/downloader/downloader.json.zip')

        print('test_full_install_remove_local_store_and_rerun B)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")
        self.assertTrue(os.path.isfile('/tmp/delme_parallel/MiSTer'))

    def test_full_install_remove_last_successful_run_corrupt_mister_and_rerun(self):
        print('test_full_install_remove_last_successful_run_corrupt_mister_and_rerun A)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")

        os.unlink('/tmp/delme_parallel/Scripts/.config/downloader/parallel.last_successful_run')
        with open('/tmp/delme_parallel/MiSTer', 'w') as f:
            f.write('corrupt')
        corrupt_hash = hash_file('/tmp/delme_parallel/MiSTer')

        print('test_full_install_remove_last_successful_run_corrupt_mister_and_rerun B)')
        self.assertRunOk("test/system/fixtures/full_install/parallel.ini")
        correct_hash = hash_file('/tmp/delme_parallel/MiSTer')

        self.assertNotEqual(correct_hash, corrupt_hash)

    def assertRunOk(self, ini_path):
        config = ConfigReader(NoLogger(), debug_env()).read_config(ini_path)
        shutil.rmtree(config[K_BASE_PATH], ignore_errors=True)
        shutil.rmtree(config[K_BASE_SYSTEM_PATH], ignore_errors=True)
        mister_path = Path('%s/MiSTer' % config[K_BASE_SYSTEM_PATH])
        os.makedirs(str(mister_path.parent), exist_ok=True)
        mister_path.touch()
        tool = str(Path(ini_path).with_suffix('.sh'))
        subprocess.run('cd ..; ./src/build.sh > src/%s' % tool, shell=True, stderr=subprocess.STDOUT)
        subprocess.run(['chmod', '+x', tool], shell=False, stderr=subprocess.STDOUT)
        test_env = os.environ.copy()
        test_env[KENV_CURL_SSL] = ''
        test_env[KENV_DEBUG] = 'true'
        result = subprocess.run([tool], stderr=subprocess.STDOUT, env=test_env)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.isfile("%s/Scripts/.config/downloader/downloader.json.zip" % config[K_BASE_SYSTEM_PATH]))
        os.unlink(tool)
