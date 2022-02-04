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
from test.objects import db_test_with_file_a, file_test_json_zip_descr, file_test_json_zip, file_a, empty_test_store
from test.fake_offline_importer import OfflineImporter


class TestOfflineImporter(unittest.TestCase):

    def setUp(self) -> None:
        self.sut = OfflineImporter()

    def test_apply_offline_databases___for_test_db_when_a_file_is_present_with_correct_hash___adds_existing_a_file_to_the_store(self):
        self.sut.file_system.test_data\
            .with_test_json_zip()\
            .with_file_a()

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_a in store['files'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___for_test_db_when_a_file_is_present_with_incorrect_hash___adds_nothing_to_the_store(self):
        self.sut.file_system.test_data\
            .with_test_json_zip()\
            .with_file_a({'hash': 'incorrect'})

        store = self.apply_db_test_with_file_a()
        self.assertFalse(file_a in store['files'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___for_test_db_when_a_file_is_present_with_ignore_hash___adds_existing_a_file_to_the_store(self):
        json_zip_db = file_test_json_zip_descr()
        json_zip_db['unzipped_json']['files'][file_a]['hash'] = 'ignore'
        self.sut.file_system.test_data\
            .with_test_json_zip(json_zip_db)\
            .with_file_a({'hash': 'incorrect'})

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_a in store['files'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_empty___adds_nothing_to_the_store(self):
        self.sut.file_system.test_data.with_test_json_zip()

        store = self.apply_db_test_with_file_a()
        self.assertFalse(file_a in store['files'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___always___adds_db_file_to_offline_databases_imported(self):
        self.sut.file_system.test_data.with_test_json_zip()

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_test_json_zip in store['offline_databases_imported'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_db_has_file_a_but_is_already_at_offline_databases_imported___just_deletes_db_file(self):
        self.sut.file_system.test_data\
            .with_test_json_zip()\
            .with_file_a()

        store = empty_test_store()
        store['offline_databases_imported'].append(file_test_json_zip)
        self.sut.add_db(db_test_with_file_a(), store)
        self.sut.apply()
        self.assertFalse(file_a in store['files'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_file_does_not_exist___does_nothing(self):
        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_test_json_zip not in store['offline_databases_imported'])
        self.assertEqual(store, empty_test_store())
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_db_id_does_not_match___does_nothing(self):
        self.sut.file_system.test_data\
            .with_test_json_zip({'hash': file_test_json_zip, 'unzipped_json': {'db_id': 'does_not_match'}})

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_test_json_zip not in store['offline_databases_imported'])
        self.assertEqual(empty_test_store(), store)
        self.assertTrue(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_db_id_is_uppercase___still_adds_db_file(self):
        unzipped_json = db_test_with_file_a().testable
        unzipped_json['db_id'] = 'TEST'

        self.sut.file_system.test_data\
            .with_test_json_zip({'hash': file_test_json_zip, 'unzipped_json': unzipped_json})

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_test_json_zip in store['offline_databases_imported'])
        self.assertFalse(self.sut.file_system.is_file(file_test_json_zip))

    def test_apply_offline_databases___when_db_id_is_not_there___does_nothing(self):
        unzipped_json = db_test_with_file_a().testable
        unzipped_json.pop('db_id')

        self.sut.file_system.test_data\
            .with_test_json_zip({'hash': file_test_json_zip, 'unzipped_json': unzipped_json})

        store = self.apply_db_test_with_file_a()
        self.assertTrue(file_test_json_zip not in store['offline_databases_imported'])
        self.assertEqual(store, empty_test_store())
        self.assertTrue(self.sut.file_system.is_file(file_test_json_zip))

    def apply_db_test_with_file_a(self):
        store = empty_test_store()
        self.sut.add_db(db_test_with_file_a(), store)
        self.sut.apply()
        return store
