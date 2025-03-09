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

from downloader.db_entity import DbEntityValidationException, check_zip
from downloader.db_entity import DbEntity
from test.objects import raw_db_empty_descr, db_empty
from test.zip_objects import zipped_nes_palettes_id, zipped_nes_palettes_desc


class TestDbEntityZips(unittest.TestCase):
    def test_construct_db_entity___with_wrong_zip_property___raises_db_entity_validation_exception(self):
        raw_db = raw_db_empty_descr()
        raw_db['zips'] = []
        self.assertRaises(DbEntityValidationException, lambda: DbEntity(raw_db, db_empty))

    def test_construct_db_entity___with_wrong_zip_because_its_empty___raises_db_entity_validation_exception(self):
        self.assertRaises(DbEntityValidationException, lambda: check_zip({}, db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_wrong_zip_field___raises_db_entity_validation_exception(self):
        for field in ['kind', 'description', 'contents_file']:
            with self.subTest(field):
                raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc()})
                raw_db['zips'][zipped_nes_palettes_id].pop(field)
                self.assertRaises(DbEntityValidationException, lambda: check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_wrong_zip_because_no_summary___raises_db_entity_validation_exception(self):
        raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc()})
        raw_db['zips'][zipped_nes_palettes_id].pop('summary_file')
        self.assertRaises(DbEntityValidationException, lambda: check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_wrong_zip_because_ambiguous_summary___raises_db_entity_validation_exception(self):
        raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc()})
        raw_db['zips'][zipped_nes_palettes_id]['internal_summary'] = {}
        self.assertRaises(DbEntityValidationException, lambda: check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_wrong_internal_zip_summary_because_of_missing_field___raises_db_entity_validation_exception(self):
        for field in {'files', 'folders'}:
            with self.subTest(field):
                raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc(summary_internal_zip_id=zipped_nes_palettes_id)})
                raw_db['zips'][zipped_nes_palettes_id]['internal_summary'].pop(field)
                self.assertRaises(DbEntityValidationException, lambda: check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_correct_internal_zip_summary___returns_db(self):
        raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc(summary_internal_zip_id=zipped_nes_palettes_id)})
        self.assertIsNone(check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))

    def test_construct_db_entity___with_wrong_zip_kind___raises_db_entity_validation_exception(self):
        for wrong_field in ['', None, 'wrong']:
            with self.subTest(wrong_field):
                raw_db = raw_db_empty_descr(zips={zipped_nes_palettes_id: zipped_nes_palettes_desc()})
                raw_db['zips'][zipped_nes_palettes_id]['kind'] = wrong_field
                self.assertRaises(DbEntityValidationException, lambda: check_zip(raw_db['zips'][zipped_nes_palettes_id], db_empty, zipped_nes_palettes_id))
