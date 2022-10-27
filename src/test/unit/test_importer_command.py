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
from downloader.constants import K_BASE_PATH, K_DOWNLOADER_RETRIES, K_OPTIONS, K_STORAGE_PRIORITY, K_FILTER
from downloader.db_options import DbOptionsKind, DbOptions
from test.fake_importer_command import ImporterCommand
from test.objects import db_entity, config_with

nil = {}
config = config_with(storage_priority='prefer_external')
config_with_options = config_with(downloader_retries=42)
db = db_entity()
db_with_options = db_entity(default_options={K_DOWNLOADER_RETRIES: 1})
ini_options = DbOptions({K_DOWNLOADER_RETRIES: 8}, kind=DbOptionsKind.INI_SECTION)


class TestImporterCommand(unittest.TestCase):

    def test_read_dbs___after_adding_nothing___returns_empty_array(self):
        self.assertEqual([], ImporterCommand(config).read_dbs())

    def test_read_dbs___after_adding_no_options___returns_original_config(self):
        actual = ImporterCommand(config)\
            .add_db(db, nil, nil)\
            .add_db(db, nil, nil)\
            .read_dbs()

        self.assert_config(config, actual[0])
        self.assert_config(config, actual[1])

    def test_read_dbs___after_adding_different_options___returns_corresponding_original_config_variants(self):
        actual = ImporterCommand(config)\
            .add_db(db, nil, {K_OPTIONS: DbOptions({K_BASE_PATH: 'abc'}, kind=DbOptionsKind.INI_SECTION)})\
            .add_db(db, nil, {K_OPTIONS: DbOptions({K_FILTER: 'arcade'}, kind=DbOptionsKind.INI_SECTION)})\
            .read_dbs()

        self.assert_config({K_BASE_PATH: 'abc', K_STORAGE_PRIORITY: 'prefer_external'}, actual[0])
        self.assert_config({K_FILTER: 'arcade', K_STORAGE_PRIORITY: 'prefer_external'}, actual[1])

    def test_read_dbs___with_config_options___returns_config_with_options(self):
        actual = ImporterCommand(config_with_options)\
            .add_db(db, nil, nil)\
            .read_dbs()[0]

        self.assert_config(config_with_options, actual)

    def test_read_dbs___with_ini_options___returns_ini_options(self):
        actual = ImporterCommand(config_with_options)\
            .add_db(db, nil, {K_OPTIONS: ini_options})\
            .read_dbs()

        self.assert_config(ini_options.testable, actual[0])

    def test_read_dbs___with_db_options___returns_db_options(self):
        actual = ImporterCommand(default_config())\
            .add_db(db_with_options, nil, nil)\
            .read_dbs()[0]

        self.assert_config(db_with_options.default_options.testable, actual)

    def test_read_dbs___with_config_and_db_options___returns_config_with_options(self):
        actual = ImporterCommand(config_with_options)\
            .add_db(db_with_options, nil, nil)\
            .read_dbs()[0]

        self.assert_config(config_with_options, actual)

    def test_read_dbs___with_config_db_and_ini_options___returns_ini_options(self):
        actual = ImporterCommand(config_with_options)\
            .add_db(db_with_options, nil, {K_OPTIONS: ini_options})\
            .read_dbs()[0]

        self.assert_config(ini_options.testable, actual)

    def test_read_dbs___after_adding_default_db_first___returns_default_db_first(self):
        actual = ImporterCommand(config_with(default_db_id='default_db_id')) \
            .add_db(db_entity(db_id='default_db_id'), nil, nil) \
            .add_db(db_entity(db_id='x'), nil, nil) \
            .read_dbs()[0][0].db_id

        self.assertEqual('default_db_id', actual)

    def test_read_dbs___after_adding_default_db_last___returns_default_db_first(self):
        actual = ImporterCommand(config_with(default_db_id='default_db_id'))\
            .add_db(db_entity(db_id='x'), nil, nil) \
            .add_db(db_entity(db_id='default_db_id'), nil, nil) \
            .read_dbs()[0][0].db_id

        self.assertEqual('default_db_id', actual)

    def assert_command(self, expected_db, expected_store, expected_config, actual):
        self.assertEqual((expected_db, expected_store, expected_config), actual)

    def assert_config(self, expected_config, actual):
        config = default_config()
        for key in expected_config:
            config[key] = expected_config[key]
        self.assertEqual(config, actual[2], "config")
