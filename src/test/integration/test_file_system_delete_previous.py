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
import tempfile
import os
from downloader.config import default_config
from downloader.constants import K_BASE_PATH, K_BASE_SYSTEM_PATH, K_ALLOW_DELETE
from test.objects import db_test_with_file, file_descr, hash_real_test_file, empty_test_store
from test.fake_online_importer import OnlineImporter
from test.fake_file_system_factory import make_production_filesystem_factory


class TestFileSystemDeletePrevious(unittest.TestCase):
    ao486_new = '_Computer/ao486_20211010.rbf'
    ao486_old = '_Computer/ao486_20201010.rbf'

    def test_delete_previous_installing_new_ao486___with_existing_old_ao486___deletes_old_ao486(self):
        with tempfile.TemporaryDirectory() as tempdir:
            os.mkdir('%s/_Computer' % tempdir)

            config = self.config(tempdir)

            file_system_factory = make_production_filesystem_factory(config)
            file_system = file_system_factory.create_for_system_scope()
            file_system.touch(self.ao486_old)
            store = empty_test_store()

            sut = OnlineImporter(config=config, file_system_factory=file_system_factory)
            sut.add_db(db_test_with_file(self.ao486_new, file_descr(delete=[True], hash_code=hash_real_test_file)), store)
            sut.download(False)

            self.assertFalse(file_system.is_file(self.ao486_old))
            self.assertTrue(file_system.is_file(self.ao486_new))

    mycore_1 = 'mycore_20210101.rbf'
    mycore_2 = 'mycore_20200101.rbf'
    mycore_3 = 'mycore_20210202.rbf'
    yourcore = 'yourcore_20200101.rbf'

    def test_delete_previous_mycore_3___with_existing_mycore_files___deletes_only_previous_mycores(self):
        with tempfile.TemporaryDirectory() as tempdir:

            config = self.config(tempdir)

            file_system_factory = make_production_filesystem_factory(config)
            file_system = file_system_factory.create_for_system_scope()
            file_system.touch(self.mycore_1)
            file_system.touch(self.mycore_2)
            file_system.touch(self.yourcore)

            self.run_delete_previous_on_mycore_3(file_system_factory, config)

            self.assertFalse(file_system.is_file(self.mycore_1))
            self.assertFalse(file_system.is_file(self.mycore_2))
            self.assertTrue(file_system.is_file(self.yourcore))

    def test_delete_previous_mycore_3___with_existing_mycore_files___doesnt_delete_wrong_regex_files(self):
        for mycore_wrong in ['mycore_2021020.rbf', 'mycore20210202.rbf', 'mycore_20210101.rbfs', 'mycore_2021a101.rbf']:
            with self.subTest(mycore_wrong) as _:
                with tempfile.TemporaryDirectory() as tempdir:
                    config = self.config(tempdir)

                    file_system_factory = make_production_filesystem_factory(config)
                    file_system = file_system_factory.create_for_system_scope()
                    file_system.touch(mycore_wrong)
                    self.run_delete_previous_on_mycore_3(file_system_factory, config)
                    self.assertTrue(file_system.is_file(mycore_wrong))

    def test_delete_previous_mycore_3___with_existing_mycore_files___deletes_all_matching_files(self):
        for mycore_correct in [self.mycore_1, 'mycore_99999999.rbf', 'mycore_00000000.rbf', 'mycore_20210101.RBF', 'MYCORE_20210101.rbf']:
            with self.subTest(mycore_correct) as _:
                with tempfile.TemporaryDirectory() as tempdir:
                    config = self.config(tempdir)

                    file_system_factory = make_production_filesystem_factory(config)
                    file_system = file_system_factory.create_for_system_scope()
                    file_system.touch(mycore_correct)
                    self.run_delete_previous_on_mycore_3(file_system_factory, config)
                    self.assertFalse(file_system.is_file(mycore_correct))

    def test_delete_previous_menucore___with_existing_menucore_files___deletes_nothing(self):
        menu_rbf = 'menu2.rbf'
        other_menu_rbf = 'menu2_20202121.rbf'
        with tempfile.TemporaryDirectory() as tempdir:
            config = self.config(tempdir)

            file_system_factory = make_production_filesystem_factory(config)
            file_system = file_system_factory.create_for_system_scope()
            file_system.touch(menu_rbf)
            file_system.touch(other_menu_rbf)

            sut = OnlineImporter(config=config, file_system_factory=file_system_factory)
            sut.add_db(db_test_with_file(menu_rbf, file_descr(delete=[True])), empty_test_store())
            sut.download(False)

            self.assertTrue(file_system.is_file(menu_rbf))
            self.assertTrue(file_system.is_file(other_menu_rbf))

    def test_delete_previous_mycore_3___with_existing_mycore_file_but_disallow_deletes___deletes_nothing(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config = self.config(tempdir)
            config[K_ALLOW_DELETE] = False

            file_system_factory = make_production_filesystem_factory(config)
            file_system = file_system_factory.create_for_system_scope()
            file_system.touch(self.mycore_1)

            self.run_delete_previous_on_mycore_3(file_system_factory, config)

            self.assertTrue(file_system.is_file(self.mycore_1))

    def run_delete_previous_on_mycore_3(self, file_system_factory, config):
        sut = OnlineImporter(config=config, file_system_factory=file_system_factory)
        sut.add_db(db_test_with_file(self.mycore_3, file_descr(delete=[True], hash_code=hash_real_test_file)), empty_test_store())
        sut.download(False)
        self.assertTrue(file_system_factory.create_for_system_scope().is_file(self.mycore_3))

    def config(self, tempdir):
        config = default_config()
        config[K_BASE_PATH] = tempdir
        config[K_BASE_SYSTEM_PATH] = tempdir
        return config
