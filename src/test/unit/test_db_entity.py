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

from typing import Any, Optional
import unittest

from downloader.config import default_config
from downloader.constants import K_BASE_PATH, FILE_MiSTer, FOLDER_gamecontrollerdb, FOLDER_linux, FILE_gamecontrollerdb, \
    FILE_gamecontrollerdb_user, DISTRIBUTION_MISTER_DB_ID
from downloader.db_entity import DbEntityValidationException, check_file, check_folders, invalid_paths, \
    no_distribution_mister_invalid_paths, invalid_root_folders, distribution_mister_exceptional_paths
from downloader.db_options import DbOptionsValidationException
from downloader.path_package import PathPackage, PathPackageKind, PathType
from downloader.db_entity import DbEntity
from test.objects import db_test, raw_db_empty_descr, db_empty, file_mister_descr, db_with_folders, file_a_descr, \
    db_test_with_file, db_entity, file_save_psx_castlevania, file_save_psx_castlevania_descr, folder_save_psx, file_a


class TestDbEntity(unittest.TestCase):

    def test_construct_db_entity___with_correct_props___returns_db(self):
        self.assertIsNotNone(DbEntity(raw_db_empty_descr(), db_empty))

    def test_construct_db_entity___with_wrong_section___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: DbEntity(raw_db_empty_descr(), 'different section'))

    def test_construct_db_entity___with_wrong_db___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: DbEntity("wrong", db_empty))

    def test_construct_db_entity___with_none_db___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: DbEntity(None, db_empty))

    def test_construct_db_entity___with_correct_props_but_uppercase_db_id___returns_db_with_lowercase_id(self):
        raw_db = {'db_id': 'BiG', 'files': {}, 'folders': {}, 'timestamp': 0}
        expected = {'db_id': 'big', 'base_files_url': '', 'db_files': [], 'files': {}, 'folders': {}, 'zips': {}, 'default_options': {}, 'timestamp': 0}

        self.assertEqual(DbEntity(expected, 'big').testable, DbEntity(raw_db, 'bIg').testable)

    def test_construct_db_entity___with_missing_mandatory_field___raises_db_entity_validation_exception(self):
        for field in ['db_id', 'files', 'folders', 'timestamp']:
            with self.subTest(field):
                raw_db = raw_db_empty_descr()
                raw_db.pop(field)
                self.assertRaises(DbEntityValidationException, lambda: DbEntity(raw_db, db_empty))

    def test_construct_db_entity___with_wrong_files___raises_db_entity_validation_exception(self):
        wrong_files = [
            ('', {}),
            (file_a, {}),
            (file_a, {**file_a_descr(), 'url': 3}),
            (file_a, {**file_a_descr(), 'url': 'bad_url'}),
            (file_a, {**file_a_descr(), 'url': 'https://adsf[asdf.com'}),
            # (file_a, {**file_a_descr(), 'reboot': 'car'}),  # No reboot validation needed as long as we strict check == True on usage.
            # (file_a, {**file_a_descr(), 'tags': '1'}),  @TODO: Should I put tags validation somewhere?
            # (file_a, {**file_a_descr(), 'tags': [2.23]}),
        ]
        for i, (fp, fd) in enumerate(wrong_files):
            with self.subTest(i):
                self.assertRaises(DbEntityValidationException, lambda: check_file(pkg(fp, fd), db_test, None))

    def test_construct_db_entity___with_saves_files_that_allow_overwrite___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file(pkg(file_save_psx_castlevania, file_save_psx_castlevania_descr(overwrite=True)), db_test, None))

    def test_construct_db_entity___with_saves_files_without_overwrite_property___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file(pkg(file_save_psx_castlevania, file_save_psx_castlevania_descr()), db_test, None))

    def test_construct_db_entity___with_saves_files_that_doesnt_allow_overwrite___returns_db(self):
        self.assertIsNotNone(db_entity(files={file_save_psx_castlevania: file_save_psx_castlevania_descr(overwrite=False)}))

    def test_construct_db_entity___with_wrong_folders___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: db_entity(folders=''))

    def test_construct_db_entity___with_saves_folders___returns_db(self):
        self.assertIsNotNone(db_entity(folders={folder_save_psx: {}}))

    def test_construct_db_entity___with_wrong_options___raises_db_entity_validation_exception(self):
        raw_db = raw_db_empty_descr()
        raw_db['default_options'] = {'allow_delete': default_config()['allow_delete']}
        self.assertRaises(DbOptionsValidationException, lambda: DbEntity(raw_db, db_empty))

    def test_construct_db_entity___with_invalid_files___raises_error(self):
        invalids = [0, 'linux/file.txt', 'linux/something/something/file.txt', '../omg.txt', 'this/is/ok/../or/nope.txt', '/tmp/no', '.hidden'] + \
                        ['%s/file.txt' % k for k in invalid_root_folders] + \
                        list(invalid_paths) + \
                        list(no_distribution_mister_invalid_paths)

        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertRaises(DbEntityValidationException, lambda: check_file(pkg(wrong_path, file_a_descr()), db_test, None))

    def test_construct_db_entity___with_invalid_root_folders___raises_error(self):
        invalids = ('linux/f', 'linux/something/something/', '../', 'this/is/ok/../or/', '/user/', '.config/') + tuple('%s/folder' % f for f in invalid_root_folders) + distribution_mister_exceptional_paths
        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertRaises(DbEntityValidationException, lambda: check_folders([pkg(wrong_path, {})], 'wrong_db'))

    def test_construct_db_entity___with_mister_file___raises_invalid_downloader_path_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file(pkg(FILE_MiSTer, file_mister_descr()), db_test, None))

    def test_construct_db_entity___valid_folders___does_not_raise_an_error(self):
        invalids = (FOLDER_linux, FOLDER_gamecontrollerdb)
        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertIsNotNone(db_with_folders('wrong_db', {wrong_path: {}}))

    def test_construct_db_entity___valid_files___does_not_raise_an_error(self):
        invalids = (FILE_gamecontrollerdb, FILE_gamecontrollerdb_user)
        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertIsNotNone(db_test_with_file('wrong_db', file_a_descr()))

    def test_construct_distribution_mister___valid_exceptional_files___does_not_raise_an_error(self):
        for wrong_path in distribution_mister_exceptional_paths:
            with self.subTest(wrong_path):
                self.assertIsNotNone(db_with_folders(DISTRIBUTION_MISTER_DB_ID, {wrong_path: {}}))


def pkg(path: str, description: Optional[dict[str, Any]] = None):
    return PathPackage(path, None, description or {}, PathType.FILE, PathPackageKind.STANDARD, None)
