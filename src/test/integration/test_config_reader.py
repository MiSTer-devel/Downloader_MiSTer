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
import configparser
from downloader.config import AllowDelete, AllowReboot, InvalidConfigParameter
from downloader.constants import K_BASE_PATH, K_BASE_SYSTEM_PATH, K_UPDATE_LINUX, K_ALLOW_REBOOT, K_ALLOW_DELETE, \
    K_DOWNLOADER_SIZE_MB_LIMIT, K_DOWNLOADER_PROCESS_LIMIT, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, K_VERBOSE, K_DATABASES, \
    K_DB_URL, K_SECTION, K_OPTIONS, MEDIA_USB2, MEDIA_USB1
from test.objects import not_found_ini, db_options, default_base_path
from test.fake_config_reader import ConfigReader


class TestConfigReader(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_config_reader___when_no_ini___returns_default_values(self):
        self.assertConfig(not_found_ini(), {
            K_UPDATE_LINUX: True,
            K_ALLOW_REBOOT: AllowReboot.ALWAYS,
            K_ALLOW_DELETE: AllowDelete.ALL,
            K_BASE_PATH: default_base_path,
            K_BASE_SYSTEM_PATH: default_base_path,
            K_DOWNLOADER_SIZE_MB_LIMIT: 100,
            K_DOWNLOADER_PROCESS_LIMIT: 300,
            K_DOWNLOADER_TIMEOUT: 300,
            K_DOWNLOADER_RETRIES: 3,
            K_VERBOSE: False,
            K_DATABASES: {'distribution_mister': {
                K_DB_URL: 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
                K_SECTION: 'distribution_mister',
            }}
        })

    def test_config_reader___when_wrong_ini_file___returns_default_values(self):
        self.assertRaises(configparser.Error, lambda: self.assertConfig("test/integration/fixtures/wrong_ini_file.ini", {}))

    def test_databases___with_single_db_ini___returns_single_db_only(self):
        self.assertEqual(databases("test/integration/fixtures/single_db.ini"), {'single': {
            K_DB_URL: 'https://single.com',
            K_SECTION: 'single',
        }})

    def test_databases___with_single_db_ini_with_correct_options___returns_single_db_only_with_all_options(self):
        self.assertEqual(databases("test/integration/fixtures/single_db_with_correct_options.ini"), {'single': {
            K_DB_URL: 'https://single.com',
            K_OPTIONS: db_options().testable,
            K_SECTION: 'single',
        }})

    def test_databases___with_single_db_ini_with_incorrect_base_path___raises_invalid_config_parameter(self):
        self.assertRaises(InvalidConfigParameter, lambda: databases("test/integration/fixtures/single_db_with_incorrect_base_path.ini"))

    def test_databases___with_single_db_ini_with_incorrect_downloader_timeout___raises_invalid_config_parameter(self):
        self.assertRaises(InvalidConfigParameter, lambda: databases("test/integration/fixtures/single_db_with_incorrect_downloader_timeout.ini"))

    def test_databases___with_repeated_db_ini___raises_invalid_config_parameter_exception(self):
        self.assertRaises(InvalidConfigParameter, lambda: databases("test/integration/fixtures/repeated_db.ini"))

    def test_databases___with_dobule_db_ini___returns_dobule_db_only(self):
        self.assertEqual(databases("test/integration/fixtures/double_db.ini"), {'single': {
            K_DB_URL: 'https://single.com',
            K_SECTION: 'single',
        }, 'double': {
            K_DB_URL: 'https://double.com',
            K_SECTION: 'double',
        }})

    def test_config_reader___with_custom_mister_ini___returns_custom_fields(self):
        self.assertConfig("test/integration/fixtures/custom_mister.ini", {
            K_UPDATE_LINUX: False,
            K_ALLOW_REBOOT: AllowReboot.NEVER,
            K_ALLOW_DELETE: AllowDelete.OLD_RBF,
            K_BASE_PATH: '/media/usb0',
            K_BASE_SYSTEM_PATH: '/media/cifs',
            K_VERBOSE: True,
            K_DATABASES: {'distribution_mister': {
                K_DB_URL: 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
                K_SECTION: 'distribution_mister',
            }},
        })

    def test_config_reader___with_invalid_base_path_ini___raises_invalid_config_parameter_exception(self):
        invalid_base_path_files = ["test/integration/fixtures/invalid_base_path_1.ini", "test/integration/fixtures/invalid_base_path_2.ini"]
        for file in invalid_base_path_files:
            with self.subTest(file):
                self.assertRaises(InvalidConfigParameter, lambda: ConfigReader().read_config(file))

    def test_config_reader___with_invalid_base_system_path_ini___raises_invalid_config_parameter_exception(self):
        self.assertRaises(InvalidConfigParameter,
                          lambda: ConfigReader().read_config("test/integration/fixtures/invalid_base_system_path.ini"))

    def test_config_reader___with_custom_mister_dbs_ini___returns_custom_fields_and_dbs(self):
        self.assertConfig("test/integration/fixtures/custom_mister_dbs.ini", {
            K_UPDATE_LINUX: False,
            K_ALLOW_REBOOT: AllowReboot.ONLY_AFTER_LINUX_UPDATE,
            K_ALLOW_DELETE: AllowDelete.NONE,
            K_BASE_PATH: MEDIA_USB1,
            K_BASE_SYSTEM_PATH: MEDIA_USB2,
            K_DATABASES: {'single': {
                K_DB_URL: 'https://single.com',
                K_SECTION: 'single',
            }, 'double': {
                K_DB_URL: 'https://double.com',
                K_SECTION: 'double',
            }},
        })

    def test_config_reader___with_db_and_distrib_empty_section_1___returns_one_db_and_defult_distrib(self):
        self.assertEqual(databases("test/integration/fixtures/db_plus_distrib_empty_section_1.ini"),
                         {'distribution_mister': {
                             K_DB_URL: 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
                             K_SECTION: 'distribution_mister',
                         }, 'one': {
                             K_DB_URL: 'https://one.com',
                             K_SECTION: 'one',
                         }, })

    def test_config_reader___with_db_and_distrib_empty_section_2___returns_one_db_and_defult_distrib(self):
        self.assertEqual(databases("test/integration/fixtures/db_plus_distrib_empty_section_2.ini"), {'one': {
            K_DB_URL: 'https://one.com',
            K_SECTION: 'one',
        }, 'distribution_mister': {
            K_DB_URL: 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
            K_SECTION: 'distribution_mister',
        }})

    def test_config_reader___with_db_and_random_empty_section_2___raises_exception(self):
        self.assertRaises(Exception,
                          lambda: databases("test/integration/fixtures/db_plus_random_empty_section.ini"))

    def assertConfig(self, path, config_vars):
        actual = ConfigReader().read_config(path)

        expected = {}

        vars_count = 0

        for key in actual:
            if key in config_vars:
                vars_count = vars_count + 1
                expected[key] = config_vars[key]
            else:
                expected[key] = actual[key]

        self.assertGreater(vars_count, 0, "No valid config_vars have been provided.")
        self.assertEqual(len(config_vars), vars_count, "Some config_vars were misspelled.")
        self.assertEqual(expected, actual)


def databases(path):
    return {k: testable(v) for k, v in (ConfigReader().read_config(path)[K_DATABASES].items())}


def testable(db):
    if K_OPTIONS in db:
        db[K_OPTIONS] = db[K_OPTIONS].testable

    return db
