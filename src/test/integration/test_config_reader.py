# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from downloader.config import AllowDelete, AllowReboot, InvalidConfigParameter
from test.objects import not_found_ini
from test.fakes import ConfigReader


class TestConfigReader(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_config_reader___when_no_ini___returns_default_values(self):
        self.assertConfig(not_found_ini(), {
            'update_linux': True,
            'parallel_update': True,
            'allow_reboot': AllowReboot.ALWAYS,
            'allow_delete': AllowDelete.ALL,
            'check_manually_deleted_files': True,
            'base_path': '/media/fat/',
            'base_system_path': '/media/fat/',
            'downloader_size_mb_limit': 100,
            'downloader_process_limit': 300,
            'downloader_timeout': 300,
            'downloader_retries': 3,
            'verbose': False,
            'databases': [{
                'db_url': 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
                'section': 'distribution_mister',
            }]
        })

    def test_databases___with_single_db_ini___returns_single_db_only(self):
        self.assertEqual(self.databases("test/integration/fixtures/single_db.ini"), [{
            'db_url': 'https://single.com',
            'section': 'Single',
        }, ])

    def test_databases___with_dobule_db_ini___returns_dobule_db_only(self):
        self.assertEqual(self.databases("test/integration/fixtures/double_db.ini"), [{
            'db_url': 'https://single.com',
            'section': 'Single',
        }, {
            'db_url': 'https://double.com',
            'section': 'Double',
        }])

    def test_config_reader___with_custom_mister_ini___returns_custom_fields(self):
        self.assertConfig("test/integration/fixtures/custom_mister.ini", {
            'update_linux': False,
            'parallel_update': False,
            'check_manually_deleted_files': True,
            'allow_reboot': AllowReboot.NEVER,
            'allow_delete': AllowDelete.OLD_RBF,
            'base_path': '/media/usb0/',
            'base_system_path': '/media/cifs/',
            'verbose': True,
            'databases': [{
                'db_url': 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
                'section': 'distribution_mister',
            }],
        })

    def test_config_reader___with_invalid_base_path_ini___raises_invalid_config_parameter_exception(self):
        self.assertRaises(InvalidConfigParameter,
                          lambda: ConfigReader().read_config("test/integration/fixtures/invalid_base_path.ini"))

    def test_config_reader___with_invalid_base_system_path_ini___raises_invalid_config_parameter_exception(self):
        self.assertRaises(InvalidConfigParameter,
                          lambda: ConfigReader().read_config("test/integration/fixtures/invalid_base_system_path.ini"))

    def test_config_reader___with_custom_mister_dbs_ini___returns_custom_fields_and_dbs(self):
        self.assertConfig("test/integration/fixtures/custom_mister_dbs.ini", {
            'update_linux': False,
            'parallel_update': True,
            'check_manually_deleted_files': False,
            'allow_reboot': AllowReboot.ONLY_AFTER_LINUX_UPDATE,
            'allow_delete': AllowDelete.NONE,
            'base_path': '/media/usb1/',
            'base_system_path': '/media/usb2/',
            'databases': [{
                'db_url': 'https://single.com',
                'section': 'Single',
            }, {
                'db_url': 'https://double.com',
                'section': 'Double',
            }],
        })

    def test_config_reader___with_db_and_distrib_empty_section_1___returns_one_db_and_defult_distrib(self):
        self.assertEqual(self.databases("test/integration/fixtures/db_plus_distrib_empty_section_1.ini"), [{
            'db_url': 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
            'section': 'distribution_mister',
        }, {
            'db_url': 'https://one.com',
            'section': 'One',
        }, ])

    def test_config_reader___with_db_and_distrib_empty_section_2___returns_one_db_and_defult_distrib(self):
        self.assertEqual(self.databases("test/integration/fixtures/db_plus_distrib_empty_section_2.ini"), [{
            'db_url': 'https://one.com',
            'section': 'One',
        }, {
            'db_url': 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
            'section': 'distribution_mister',
        }, ])

    def test_config_reader___with_db_and_random_empty_section_2___raises_exception(self):
        self.assertRaises(Exception,
                          lambda: self.databases("test/integration/fixtures/db_plus_random_empty_section.ini"))

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
        self.assertEqual(actual, expected)

    def databases(self, path):
        return ConfigReader().read_config(path)['databases']
