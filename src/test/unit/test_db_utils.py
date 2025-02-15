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

from downloader.config import default_config
from downloader.constants import K_DOWNLOADER_RETRIES, K_OPTIONS, K_STORAGE_PRIORITY, STORAGE_PRIORITY_PREFER_EXTERNAL
from downloader.db_options import DbOptions
from downloader.db_utils import sorted_db_sections
from downloader.jobs.process_db_main_worker import build_db_config
from test.objects import db_entity, config_with

nil = {}
config = config_with(storage_priority=STORAGE_PRIORITY_PREFER_EXTERNAL)
config_with_options = config_with(downloader_retries=42)
db = db_entity()
db_with_options = db_entity(default_options={K_DOWNLOADER_RETRIES: 1})
ini_options = DbOptions({K_DOWNLOADER_RETRIES: 8})


class TestDbUtils(unittest.TestCase):

    def test_build_db_config___after_adding_no_options___returns_original_config(self):
        self.assert_config(config, (config, db, nil))

    def test_build_db_config___after_adding_different_options___returns_corresponding_original_config_variants(self):
        self.assert_config({'downloader_threads_limit': 32, K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_EXTERNAL}, (config, db, {K_OPTIONS: DbOptions({'downloader_threads_limit': 32})}))
        self.assert_config({'filter': 'arcade', K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_EXTERNAL}, (config, db, {K_OPTIONS: DbOptions({'filter': 'arcade'})}))

    def test_build_db_config___with_config_options___returns_config_with_options(self):
        self.assert_config(config_with_options, (config_with_options, db, nil))

    def test_build_db_config___with_ini_options___returns_ini_options(self):
        self.assert_config(ini_options.testable, (config_with_options, db, {K_OPTIONS: ini_options}))

    def test_build_db_config___with_db_options___returns_db_options(self):
        self.assert_config(db_with_options.default_options.testable, (default_config(), db_with_options, nil))

    def test_build_db_config___with_config_and_db_options___returns_config_with_options(self):
        self.assert_config(config_with_options, (config_with_options, db_with_options, nil))

    def test_build_db_config___with_config_db_and_ini_options___returns_ini_options(self):
        self.assert_config(ini_options.testable, (config_with_options, db_with_options, {K_OPTIONS: ini_options}))

    def test_sorted_db_sections___after_adding_nothing___returns_empty_array(self):
        self.assertEqual([], sorted_db_sections(config))

    def test_sorted_db_sections___after_adding_default_db_first___returns_default_db_first(self):
        actual, _ = sorted_db_sections(config_with(default_db_id='default_db_id', databases={'default_db_id': db, 'x': db_with_options}))[0]
        self.assertEqual('default_db_id', actual)

    def test_sorted_db_sections___after_adding_default_db_last___returns_default_db_first(self):
        actual, _ = sorted_db_sections(config_with(default_db_id='default_db_id', databases={'x': db_with_options, 'default_db_id': db}))[0]
        self.assertEqual('default_db_id', actual)

    def assert_command(self, expected_db, expected_store, expected_config, actual):
        self.assertEqual((expected_db, expected_store, expected_config), actual)

    def assert_config(self, expected, input):
        in_config, in_db, in_ini = input
        user_defined_options = []
        for key, value in default_config().items():
            if key in in_config and value != in_config[key]:
                user_defined_options.append(key)

        actual = build_db_config({**in_config, 'user_defined_options': user_defined_options}, in_db, in_ini)

        config = default_config()
        for key in expected:
            config[key] = expected[key]

        config['user_defined_options'] = user_defined_options

        self.assertEqual(config, actual, "config")