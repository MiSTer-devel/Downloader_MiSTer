# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.db_entity import DbEntityValidationException, check_zip_summary, rename_archive_to_zip_fields, rename_archive_summaries_to_zip_fields
from downloader.db_entity import DbEntity
from test.objects import raw_db_empty_descr, db_empty, archive_nes_palettes_id
from test.zip_objects import nes_palettes_desc


second_archive_id = 'second_archive'
second_archive_description = 'Extracting Second Archive'


class TestDbEntityArchives(unittest.TestCase):
    def test_rename_archive_to_zip_fields___on_archive_desc___equals_zip_desc(self):
        archive = nes_palettes_desc(summary_internal_id=archive_nes_palettes_id)
        renamed = rename_archive_to_zip_fields(archive)
        rename_archive_summaries_to_zip_fields(renamed.get('internal_summary', {}))
        expected = nes_palettes_desc(summary_internal_id=archive_nes_palettes_id, zip_fields=True)
        self.assertEqual(expected, renamed)

    def test_construct_db_entity___with_wrong_archives_property___raises_db_entity_validation_exception(self):
        raw_db = raw_db_empty_descr()
        raw_db['archives'] = []
        self.assertRaises(DbEntityValidationException, lambda: DbEntity(raw_db, db_empty))

    def test_construct_db_entity___with_archives_only___populates_zips(self):
        raw_db = raw_db_empty_descr()
        raw_db['archives'] = {archive_nes_palettes_id: nes_palettes_desc(summary_internal_id=archive_nes_palettes_id)}
        db = DbEntity(raw_db, db_empty)
        self.assertIn(archive_nes_palettes_id, db.zips)

    def test_construct_db_entity___with_zips_field___adds_format_zip_automatically(self):
        raw_db = raw_db_empty_descr()
        raw_db['zips'] = {archive_nes_palettes_id: nes_palettes_desc(summary_internal_id=archive_nes_palettes_id, zip_fields=True)}
        db = DbEntity(raw_db, db_empty)
        self.assertEqual(db.zips[archive_nes_palettes_id]['format'], 'zip')

    def test_construct_db_entity___with_both_archives_and_zips_no_conflict___merges_both(self):
        raw_db = raw_db_empty_descr()
        raw_db['zips'] = {archive_nes_palettes_id: nes_palettes_desc(summary_internal_id=archive_nes_palettes_id, zip_fields=True)}
        raw_db['archives'] = {second_archive_id: _second_archive_desc()}
        db = DbEntity(raw_db, db_empty)
        self.assertIn(archive_nes_palettes_id, db.zips)
        self.assertIn(second_archive_id, db.zips)

    def test_construct_db_entity___with_archives_overriding_zips___archives_wins(self):
        raw_db = raw_db_empty_descr()
        raw_db['zips'] = {archive_nes_palettes_id: nes_palettes_desc(summary_internal_id=archive_nes_palettes_id, zip_fields=True)}
        raw_db['archives'] = {archive_nes_palettes_id: _second_archive_desc()}
        db = DbEntity(raw_db, db_empty)
        self.assertEqual(db.zips[archive_nes_palettes_id]['description'], second_archive_description)
        self.assertIn('contents_file', db.zips[archive_nes_palettes_id])
        self.assertNotIn('archive_file', db.zips[archive_nes_palettes_id])

    def test_construct_db_entity___with_empty_archives___results_in_empty_zips(self):
        raw_db = raw_db_empty_descr()
        raw_db['archives'] = {}
        db = DbEntity(raw_db, db_empty)
        self.assertEqual(db.zips, {})

    def test_construct_db_entity___with_no_archives_and_no_zips___results_in_empty_zips(self):
        raw_db = raw_db_empty_descr()
        db = DbEntity(raw_db, db_empty)
        self.assertEqual(db.zips, {})

    # Field renames: archives new names are mapped to zips legacy names

    def test_archive_file___is_renamed_to___contents_file(self):
        result = rename_archive_to_zip_fields(_new_archive_desc())
        self.assertIn('contents_file', result)
        self.assertNotIn('archive_file', result)

    def test_summary_inline___is_renamed_to___internal_summary(self):
        desc = _new_archive_desc()
        desc.pop('summary_file')
        desc['summary_inline'] = {'files': {}, 'folders': {}}
        result = rename_archive_to_zip_fields(desc)
        self.assertIn('internal_summary', result)
        self.assertNotIn('summary_inline', result)

    def test_target_folder___is_renamed_to___target_folder_path(self):
        result = rename_archive_to_zip_fields(_new_archive_desc())
        self.assertEqual(result['target_folder_path'], 'games/SNES/')
        self.assertNotIn('target_folder', result)

    def test_arc_id___is_renamed_to___zip_id___in_summary_files(self):
        summary = _summary_with_arc_fields()
        check_zip_summary(summary, db_empty, 'test_archive')
        self.assertEqual(summary['files']['games/NES/palette.pal']['zip_id'], 'test_archive')
        self.assertNotIn('arc_id', summary['files']['games/NES/palette.pal'])

    def test_arc_id___is_renamed_to___zip_id___in_summary_folders(self):
        summary = _summary_with_arc_fields()
        check_zip_summary(summary, db_empty, 'test_archive')
        self.assertEqual(summary['folders']['games/NES']['zip_id'], 'test_archive')
        self.assertNotIn('arc_id', summary['folders']['games/NES'])

    def test_arc_at___is_renamed_to___zip_path___in_summary_files(self):
        summary = _summary_with_arc_fields()
        check_zip_summary(summary, db_empty, 'test_archive')
        self.assertEqual(summary['files']['games/NES/palette.pal']['zip_path'], 'palette.pal')
        self.assertNotIn('arc_at', summary['files']['games/NES/palette.pal'])

    def test_extract_all___is_renamed_to___extract_all_contents(self):
        result = rename_archive_to_zip_fields(_new_archive_desc())
        self.assertEqual(result['kind'], 'extract_all_contents')

    def test_extract_selective___is_renamed_to___extract_single_files(self):
        desc = _new_archive_desc()
        desc['extract'] = 'selective'
        result = rename_archive_to_zip_fields(desc)
        self.assertEqual(result['kind'], 'extract_single_files')


def _summary_with_arc_fields():
    return {
        'files': {'games/NES/palette.pal': {'hash': 'aa' * 16, 'size': 192, 'arc_id': 'test_archive', 'arc_at': 'palette.pal'}},
        'folders': {'games/NES': {'arc_id': 'test_archive'}}
    }


def _second_archive_desc():
    return {
        "format": "zip",
        "extract": "all",
        "base_files_url": "https://base_files_url",
        "description": second_archive_description,
        "archive_file": {
            "hash": "abcdef1234567890abcdef1234567890",
            "size": 1000,
            "url": "https://contents_file_2"
        },
        "target_folder": "games/SNES/",
        "summary_file": {
            "hash": "1234567890abcdef1234567890abcdef",
            "size": 500,
            "url": "https://summary_file_2"
        }
    }


def _new_archive_desc():
    """Archive description using the new field names from docs/archives.md"""
    return {
        "format": "zip",
        "extract": "all",
        "description": "Extracting Test Archive",
        "target_folder": "games/SNES/",
        "archive_file": {
            "hash": "abcdef1234567890abcdef1234567890",
            "size": 1000,
            "url": "https://archive_file_url"
        },
        "summary_file": {
            "hash": "1234567890abcdef1234567890abcdef",
            "size": 500,
            "url": "https://summary_file_url"
        }
    }
