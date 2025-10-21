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
from downloader.constants import FILE_MiSTer, FOLDER_gamecontrollerdb, FOLDER_linux, FILE_gamecontrollerdb, \
    FILE_gamecontrollerdb_user, DISTRIBUTION_MISTER_DB_ID
from downloader.db_entity import DbEntityValidationException, check_file_pkg, check_folder_paths, invalid_paths, \
    no_distribution_mister_invalid_paths, invalid_root_folders, distribution_mister_exceptional_paths, \
    DbVersionUnsupportedException
from downloader.db_options import DbOptionsValidationException
from downloader.path_package import PathPackage, PathPackageKind, PathType
from downloader.db_entity import DbEntity
from objects import zipped_nes_palettes_id
from test.objects import db_test, raw_db_empty_descr, db_empty, file_mister_descr, db_with_folders, file_a_descr, \
    db_test_with_file, db_entity, file_save_psx_castlevania, file_save_psx_castlevania_descr, folder_save_psx, file_a, \
    folder_a, file_nes_smb1, file_nes_smb1_descr, folder_games, folder_games_nes, zip_index_entity
from test.objects_old_pext import file_nes_smb1 as file_nes_smb1_old_pext, \
    db_entity as db_entity_old_pext, file_nes_smb1_descr as file_nes_smb1_descr_old_pext, \
    folder_games as folder_games_old_pext, folder_games_nes as folder_games_nes_old_pext
from test.zip_objects_old_pext import zipped_nes_palettes_desc as zipped_nes_palettes_desc_old_pext, zipped_nes_palettes_id as zipped_nes_palettes_id_old_pext
from zip_objects import zipped_nes_palettes_desc


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

        self.assertEqual(DbEntity(expected, 'big').extract_props(), DbEntity(raw_db, 'bIg').extract_props())

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
                self.assertRaises(DbEntityValidationException, lambda: check_file_pkg(pkg(fp, fd), db_test, None))

    def test_construct_db_entity___with_saves_files_that_allow_overwrite___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file_pkg(pkg(file_save_psx_castlevania, file_save_psx_castlevania_descr(overwrite=True)), db_test, None))

    def test_construct_db_entity___with_saves_files_without_overwrite_property___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file_pkg(pkg(file_save_psx_castlevania, file_save_psx_castlevania_descr()), db_test, None))

    def test_construct_db_entity___with_saves_files_that_doesnt_allow_overwrite___returns_db(self):
        self.assertIsNotNone(db_entity(files={file_save_psx_castlevania: file_save_psx_castlevania_descr(overwrite=False)}))

    def test_construct_db_entity___with_wrong_folders___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: db_entity(folders=''))

    def test_construct_db_entity___with_saves_folders___returns_db(self):
        self.assertIsNotNone(db_entity(folders={folder_save_psx: {}}))

    def test_construct_db_entity___with_some_incorrect_prop___raises_db_entity_validation_exception(self):
        wrong_props = [
            ('v', -1),
            ('v', 0.0),
            ('files', 'not_a_dict'),
            ('folders', 'not_a_dict'),
            ('timestamp', 'not_an_int'),
        ]
        for prop, value in wrong_props:
            with self.subTest(prop):
                raw_db = raw_db_empty_descr()
                raw_db[prop] = value
                self.assertRaises(DbEntityValidationException, lambda: DbEntity(raw_db, db_empty))

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
                self.assertRaises(DbEntityValidationException, lambda: check_file_pkg(pkg(wrong_path, file_a_descr()), db_test, None))

    def test_construct_db_entity___with_invalid_root_folders___raises_error(self):
        invalids = ('linux/f', 'linux/something/something/', '../', 'this/is/ok/../or/', '/user/', '.config/') + tuple('%s/folder' % f for f in invalid_root_folders) + distribution_mister_exceptional_paths
        for wrong_path in invalids:
            with self.subTest(wrong_path):
                self.assertRaises(DbEntityValidationException, lambda: check_folder_paths([pkg(wrong_path, {})], 'wrong_db'))

    def test_construct_db_entity___with_mister_file___raises_invalid_downloader_path_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_file_pkg(pkg(FILE_MiSTer, file_mister_descr()), db_test, None))

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

    def test_migrate_db___on_db_from_v0_to_v1___returns_expected_db(self):
        db_v0 = db_entity_old_pext(
            files={file_nes_smb1_old_pext: file_nes_smb1_descr_old_pext(), file_a: file_a_descr()},
            folders=[folder_games_old_pext, folder_games_nes_old_pext, folder_a]
        )

        self.assertTrue(db_v0.needs_migration())
        error = db_v0.migrate()
        self.assertIsNone(error)
        self.assertFalse(db_v0.needs_migration())

        self.assertEqual(db_entity(
            files={file_nes_smb1: file_nes_smb1_descr(), file_a: file_a_descr()},
            folders={folder_games: {'path': 'pext'}, folder_games_nes: {'path': 'pext'}, folder_a: {}},
            timestamp=0
        ).extract_props(), db_v0.extract_props())

    def test_migrate_db___with_unsupported_version___returns_exception(self):
        db = db_entity(files={file_a: file_a_descr()}, folders={folder_a: {}}, version=999)
        self.assertTrue(db.needs_migration())
        self.assertIsInstance(db.migrate(), DbVersionUnsupportedException)

    def test_migrate_zip_index___on_db_from_v0_to_v1___returns_expected_db(self):
        zip_index = zip_index_entity(
            files={file_nes_smb1_old_pext: file_nes_smb1_descr_old_pext(), file_a: file_a_descr()},
            folders={folder_games_old_pext: {}, folder_games_nes_old_pext: {}, folder_a: {}},
            version=0
        )
        self.assertTrue(zip_index.needs_migration())
        error = zip_index.migrate(db_test)
        self.assertIsNone(error)
        self.assertFalse(zip_index.needs_migration())

        self.assertEqual(zip_index_entity(
            files={file_nes_smb1: file_nes_smb1_descr(), file_a: file_a_descr()},
            folders={folder_games: {'path': 'pext'}, folder_games_nes: {'path': 'pext'}, folder_a: {}},
            version=1
        ), zip_index)

    def test_migrate_zip_index___with_unsupported_Version___returns_exception(self):
        zip_index = zip_index_entity(files={file_a: file_a_descr()}, folders={folder_a: {}}, version=999)
        self.assertTrue(zip_index.needs_migration())
        self.assertIsInstance(zip_index.migrate(db_test), DbVersionUnsupportedException)

    def test_migrate_db_with_internal_zip_summary___on_db_from_v0_to_v1___returns_expected_db(self):
        db_v0 = db_entity_old_pext(zips={zipped_nes_palettes_id_old_pext: zipped_nes_palettes_desc_old_pext(summary_internal_zip_id=zipped_nes_palettes_id_old_pext)})

        self.assertTrue(db_v0.needs_migration())
        error = db_v0.migrate()
        self.assertIsNone(error)
        self.assertFalse(db_v0.needs_migration())

        actual = db_v0.extract_props()
        expected = db_entity(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc(summary_internal_zip_id=zipped_nes_palettes_id)}).extract_props()
        del actual['zips'][zipped_nes_palettes_id]['contents_file']['zipped_files']
        del expected['zips'][zipped_nes_palettes_id]['contents_file']['zipped_files']
        self.assertEqual(expected, actual)


def pkg(path: str, description: Optional[dict[str, Any]] = None):
    return PathPackage(path, None, description or {}, PathType.FILE, PathPackageKind.STANDARD, None)
