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

from downloader.config import InvalidConfigParameter
from downloader.constants import DISTRIBUTION_MISTER_DB_ID, DISTRIBUTION_MISTER_DB_URL
from test.fake_config_reader import ConfigReader
from test.objects import ini


base_id = 'base_db'
base_db = {'db_url': 'https://base.com'}
extra_id = 'extra_db'
extra_db = {'db_url': 'https://extra.com'}
arcade_id = 'arcade_db'
arcade_db = {'db_url': 'https://arcade.com', 'filter': 'arcade'}
db1_id = 'db1'
db1 = {'db_url': 'https://1.com'}
db2_id = 'db2'
db2 = {'db_url': 'https://2.com'}


class TestConfigReaderDownloaderIniExtensions(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def read_config(self, files: dict):
        config_path = next(iter(files))
        reader = ConfigReader(file_contents=files)
        result = reader.read_config(config_path)
        result['databases'] = _make_comparable(result['databases'])
        return result

    # --- File Discovery ---

    def test_read_config___with_no_drop_ins___returns_base_databases_only(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
        }))

        self.assertEqual(databases({base_id: base_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_one_drop_in___returns_base_plus_drop_in_database(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/extra.ini': ini({extra_id: extra_db}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_multiple_drop_ins___returns_all_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/extra.ini': ini({extra_id: extra_db}),
            'downloader/arcade.ini': ini({arcade_id: arcade_db}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db, arcade_id: arcade_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_downloader_d_and_downloader_star_ini___loads_downloader_d_first(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader_star.ini': ini({db2_id: db2}),
            'downloader/extra.ini': ini({db1_id: db1}),
        }))

        self.assertEqual(list(sut['databases'].keys()), [base_id, db1_id, db2_id])

    # --- File Eligibility Filter ---

    def test_read_config___with_ineligible_drop_in_files___skips_them(self):
        ineligible_files = [
            ('.hidden.ini', 'dotfile'),
            ('backup.ini~', 'tilde backup'),
            ('backup.ini.bak', 'bak file'),
            ('temp.ini.swp', 'swp file'),
            ('notes.txt', 'non-ini extension'),
            ('readme.md', 'non-ini extension'),
        ]
        for filename, reason in ineligible_files:
            with self.subTest(f'{filename} ({reason})'):
                sut = self.read_config(fs({
                    'downloader.ini': ini({base_id: base_db}),
                    f'downloader/{filename}': ini({extra_id: extra_db}),
                }))

                self.assertEqual(databases({base_id: base_db}), sut['databases'])
                self.assertEqual([], sut['ignored_databases'])

    # --- Drop-in Validation ---

    def test_read_config___with_drop_in_containing_multiple_sections___returns_all_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/extra.ini': ini({
                db1_id: db1,
                db2_id: db2,
            }),
        }))

        self.assertEqual(databases({base_id: base_db, db1_id: db1, db2_id: db2}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_drop_in_containing_mister_section___raises_error(self):
        cases = [
            ('single section', ini({'mister': {'verbose': 'true'}})),
            ('multi section', ini({'mister': {'verbose': 'true'}, db1_id: db1})),
        ]
        for label, drop_in in cases:
            with self.subTest(label):
                self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
                    'downloader.ini': ini({base_id: base_db}),
                    'downloader/bad.ini': drop_in,
                })))

    def test_read_config___with_drop_in_containing_distribution_mister_section___raises_error(self):
        distribution_db = {'db_url': 'https://distribution.com'}
        cases = [
            ('single section', ini({DISTRIBUTION_MISTER_DB_ID: distribution_db})),
            ('multi section', ini({DISTRIBUTION_MISTER_DB_ID: distribution_db, db1_id: db1})),
        ]
        for label, drop_in in cases:
            with self.subTest(label):
                self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
                    'downloader.ini': ini({base_id: base_db}),
                    'downloader/bad.ini': drop_in,
                })))

    def test_read_config___with_drop_in_containing_distribution_mister_section___raises_error_also_for_star_pattern(self):
        distribution_db = {'db_url': 'https://distribution.com'}
        self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader_bad.ini': ini({DISTRIBUTION_MISTER_DB_ID: distribution_db}),
        })))

    def test_read_config___with_drop_in_missing_db_url___raises_invalid_config_parameter(self):
        cases = [
            ('single section', ini({'some_db': {'filter': 'arcade'}})),
            ('multi section', ini({db1_id: db1, 'some_db': {'filter': 'arcade'}})),
        ]
        for label, drop_in in cases:
            with self.subTest(label):
                self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
                    'downloader.ini': ini({base_id: base_db}),
                    'downloader/bad.ini': drop_in,
                })))

    def test_read_config___with_star_drop_in___returns_base_plus_drop_in_database(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader_extra.ini': ini({extra_id: extra_db}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_drop_in_containing_zero_sections___adds_to_ignored_databases_with_no_db_id(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/commented_out.ini': '# [arcade/db]\n# db_url = https://arcade.com\n',
        }))

        self.assertEqual(databases({base_id: base_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader/commented_out.ini', 'reason': 'empty'}], sut['ignored_databases'])

    # --- Duplicate Database ID ---

    def test_read_config___with_duplicate_id_from_base___keeps_base_and_adds_to_ignored_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/extra.ini': ini({base_id: extra_db}),
        }))

        self.assertEqual(databases({base_id: base_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader/extra.ini', 'db_id': base_id, 'reason': 'duplicate', 'ctx': 'downloader.ini'}], sut['ignored_databases'])

    def test_read_config___with_duplicate_id_from_earlier_drop_in___keeps_first_and_adds_to_ignored_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/a_extra.ini': ini({extra_id: extra_db}),
            'downloader/b_extra.ini': ini({extra_id: db1}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader/b_extra.ini', 'db_id': extra_id, 'reason': 'duplicate', 'ctx': 'downloader/a_extra.ini'}], sut['ignored_databases'])

    def test_read_config___with_multi_section_drop_in_where_one_duplicates_base___keeps_new_and_ignores_duplicate(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/mixed.ini': ini({base_id: extra_db, db1_id: db1}),
        }))

        self.assertEqual(databases({base_id: base_db, db1_id: db1}), sut['databases'])
        self.assertEqual([{'file': 'downloader/mixed.ini', 'db_id': base_id, 'reason': 'duplicate', 'ctx': 'downloader.ini'}], sut['ignored_databases'])

    def test_read_config___with_multi_section_drop_in_where_all_duplicate_base___ignores_all(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db, db1_id: db1}),
            'downloader/mixed.ini': ini({base_id: extra_db, db1_id: db2}),
        }))

        self.assertEqual(databases({base_id: base_db, db1_id: db1}), sut['databases'])
        self.assertEqual([
            {'file': 'downloader/mixed.ini', 'db_id': base_id, 'reason': 'duplicate', 'ctx': 'downloader.ini'},
            {'file': 'downloader/mixed.ini', 'db_id': db1_id, 'reason': 'duplicate', 'ctx': 'downloader.ini'},
        ], sut['ignored_databases'])

    # --- Default Distribution Database ---

    def test_read_config___with_no_databases_in_base_ini_but_drop_in_present___adds_default_distribution_db(self):
        sut = self.read_config(fs({
            'downloader.ini': '',
            'downloader/extra.ini': ini({extra_id: extra_db}),
        }))

        distribution_db = {'db_url': DISTRIBUTION_MISTER_DB_URL}
        self.assertEqual(databases({DISTRIBUTION_MISTER_DB_ID: distribution_db, extra_id: extra_db}), sut['databases'])

    def test_read_config___with_database_in_base_ini_and_drop_in___does_not_add_default_distribution_db(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/extra.ini': ini({extra_id: extra_db}),
        }))

        self.assertNotIn(DISTRIBUTION_MISTER_DB_ID, sut['databases'])
        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])

    # --- Drop-in Database Parsing ---

    def test_read_config___with_drop_in_having_db_url_and_filter___returns_database_with_options(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/arcade.ini': ini({arcade_id: arcade_db}),
        }))

        self.assertEqual(databases({base_id: base_db, arcade_id: arcade_db}), sut['databases'])

    def test_read_config___with_drop_in_having_slash_in_section_id___returns_database_with_slash_id(self):
        slash_id = 'arcade/db'
        slash_db = db('https://arcade.com')
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader/arcade.ini': ini({slash_id: slash_db}),
        }))

        self.assertEqual(databases({base_id: base_db, slash_id: slash_db}), sut['databases'])


def db(db_url: str, **kwargs) -> dict:
    result = {'db_url': db_url}
    result.update(kwargs)
    return result


def fs(files: dict):
    return files


def databases(sections: dict) -> dict[str, dict]:
    result = {}
    for section_id, props in sections.items():
        entry = {'section': section_id, 'db_url': props['db_url']}
        non_db_keys = {k: v for k, v in props.items() if k != 'db_url'}
        if non_db_keys:
            entry['options'] = non_db_keys
        result[section_id] = entry
    return result


def _make_comparable(dbs: dict) -> dict:
    result = {}
    for k, v in dbs.items():
        entry = dict(v)
        if 'options' in entry:
            entry['options'] = entry['options'].unwrap_props()
        result[k] = entry
    return result
