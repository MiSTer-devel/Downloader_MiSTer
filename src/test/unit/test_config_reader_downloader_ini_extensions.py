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

import configparser
import unittest

from downloader.config import InvalidConfigParameter, ConfigDatabaseSection
from downloader.config_reader import ConfigReader
from test.fake_logger import NoLogger
from test.objects import default_env, ini


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


class FakeConfigReader(ConfigReader):
    def __init__(self, file_contents: dict):
        super().__init__(NoLogger(), default_env(), 0)
        self._file_contents = file_contents

    def _load_ini_config(self, config_path) -> configparser.ConfigParser:
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        content = self._file_contents.get(config_path, '')
        ini_config.read_string(content)
        return ini_config

    def _discover_drop_in_files(self, config_path: str) -> list[str]:
        base_name = config_path.rsplit('/', 1)[0] if '/' in config_path else ''
        prefix = (base_name + '/') if base_name else ''

        d_files = []
        star_files = []
        for path in self._file_contents:
            if path == config_path:
                continue
            rel = path[len(prefix):] if path.startswith(prefix) else path
            basename = rel.rsplit('/', 1)[-1]
            if not basename.endswith('.ini') or basename.startswith('.'):
                continue
            if rel.startswith('downloader.d/'):
                d_files.append(path)
            elif rel.startswith('downloader_'):
                star_files.append(path)

        return sorted(d_files) + sorted(star_files)

    def _load_drop_in_ini(self, drop_in_path: str) -> configparser.ConfigParser:
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        content = self._file_contents.get(drop_in_path, '')
        ini_config.read_string(content)
        return ini_config


class TestConfigReaderDownloaderIniExtensions(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def read_config(self, files: dict):
        config_path = next(iter(files))
        reader = FakeConfigReader(files)
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
            'downloader.d/extra.ini': ini({extra_id: extra_db}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_multiple_drop_ins___returns_all_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/extra.ini': ini({extra_id: extra_db}),
            'downloader.d/arcade.ini': ini({arcade_id: arcade_db}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db, arcade_id: arcade_db}), sut['databases'])
        self.assertEqual([], sut['ignored_databases'])

    def test_read_config___with_downloader_d_and_downloader_star_ini___loads_downloader_d_first(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader_star.ini': ini({db2_id: db2}),
            'downloader.d/extra.ini': ini({db1_id: db1}),
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
                    f'downloader.d/{filename}': ini({extra_id: extra_db}),
                }))

                self.assertEqual(databases({base_id: base_db}), sut['databases'])
                self.assertEqual([], sut['ignored_databases'])

    # --- Drop-in Validation ---

    def test_read_config___with_drop_in_containing_multiple_sections___raises_error(self):
        self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/extra.ini': ini({
                db1_id: db1,
                db2_id: db2,
            }),
        })))

    def test_read_config___with_drop_in_containing_mister_section___raises_error(self):
        self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/bad.ini': ini({'mister': {'verbose': 'true'}}),
        })))

    def test_read_config___with_drop_in_missing_db_url___raises_invalid_config_parameter(self):
        self.assertRaises(InvalidConfigParameter, lambda: self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/bad.ini': ini({'some_db': {'filter': 'arcade'}}),
        })))

    def test_read_config___with_drop_in_containing_zero_sections___adds_to_ignored_databases_with_no_db_id(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/commented_out.ini': '# [arcade/db]\n# db_url = https://arcade.com\n',
        }))

        self.assertEqual(databases({base_id: base_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader.d/commented_out.ini', 'reason': 'empty'}], sut['ignored_databases'])

    # --- Duplicate Database ID ---

    def test_read_config___with_duplicate_id_from_base___keeps_base_and_adds_to_ignored_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/extra.ini': ini({base_id: extra_db}),
        }))

        self.assertEqual(databases({base_id: base_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader.d/extra.ini', 'db_id': base_id, 'reason': 'duplicate', 'ctx': 'downloader.ini'}], sut['ignored_databases'])

    def test_read_config___with_duplicate_id_from_earlier_drop_in___keeps_first_and_adds_to_ignored_databases(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/a_extra.ini': ini({extra_id: extra_db}),
            'downloader.d/b_extra.ini': ini({extra_id: db1}),
        }))

        self.assertEqual(databases({base_id: base_db, extra_id: extra_db}), sut['databases'])
        self.assertEqual([{'file': 'downloader.d/b_extra.ini', 'db_id': extra_id, 'reason': 'duplicate', 'ctx': 'downloader.d/a_extra.ini'}], sut['ignored_databases'])

    # --- Drop-in Database Parsing ---

    def test_read_config___with_drop_in_having_db_url_and_filter___returns_database_with_options(self):
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/arcade.ini': ini({arcade_id: arcade_db}),
        }))

        self.assertEqual(databases({base_id: base_db, arcade_id: arcade_db}), sut['databases'])

    def test_read_config___with_drop_in_having_slash_in_section_id___returns_database_with_slash_id(self):
        slash_id = 'arcade/db'
        slash_db = db('https://arcade.com')
        sut = self.read_config(fs({
            'downloader.ini': ini({base_id: base_db}),
            'downloader.d/arcade.ini': ini({slash_id: slash_db}),
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
