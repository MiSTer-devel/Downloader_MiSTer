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

from downloader.constants import K_FILTER
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_file_system_factory import first_fake_temp_file, FileSystemFactory
from test.fake_full_run_service import FullRunService
from test.fake_online_importer import ImporterCommandFactorySpy
from test.objects import config_test_with_filters, db_test_with_default_filter_descr


class TestFullProducedImporterCommands(unittest.TestCase):

    def test_config_filter_SNES___with_no_overrides___forwards_SNES_to_output_filter(self):
        self.assertForwardsToOutputFilter('SNES', config_filter='SNES')

    def test_config_filter_SNES___with_ini_override_GB___forwards_GB_to_output_filter(self):
        self.assertForwardsToOutputFilter('GB', config_filter='SNES', ini_filter='GB')

    def test_config_filter_SNES___with_ini_inheritance_GB___forwards_SNES_GB_to_output_filter(self):
        self.assertForwardsToOutputFilter('SNES GB', config_filter='SNES', ini_filter='[mister] GB')

    def test_config_filter_SNES___with_db_default_options_override_GB___forwards_SNES_to_output_filter(self):
        self.assertForwardsToOutputFilter('SNES', config_filter='SNES', db_default_option_filter='GB')

    def test_config_filter_SNES___with_db_default_options_inheritance_GB___forwards_SNES_GB_to_output_filter(self):
        self.assertForwardsToOutputFilter('SNES GB', config_filter='SNES', db_default_option_filter='[mister] GB')

    def test_config_filter_SNES___with_ini_override_PSX___and_db_default_options_override_SMS___forwards_PSX_to_output_filter(self):
        self.assertForwardsToOutputFilter('PSX', config_filter='SNES', ini_filter='PSX', db_default_option_filter='SMS')

    def test_config_filter_SNES___with_ini_inheritance_PSX___and_db_default_options_inheritance_SMS___forwards_SNES_PSX_to_output_filter(self):
        self.assertForwardsToOutputFilter('SNES PSX', config_filter='SNES', ini_filter='[mister] PSX', db_default_option_filter='[mister] SMS')

    def test_no_config_filter___with_no_overrides___forwards_no_output_filter(self):
        self.assertForwardsToOutputFilter(None, config_filter=None)

    def test_no_config_filter___with_ini_override_GB___forwards_GB_to_output_filter(self):
        self.assertForwardsToOutputFilter('GB', config_filter=None, ini_filter='GB')

    def test_no_config_filter___with_db_default_options_override_GB___forwards_GB_to_output_filter(self):
        self.assertForwardsToOutputFilter('GB', config_filter=None, db_default_option_filter='GB')

    def assertForwardsToOutputFilter(self, output_filter, config_filter, ini_filter=None, db_default_option_filter=None):
        self.maxDiff = None
        config = config_test_with_filters(config_filter, ini_filter)
        fsf = FileSystemFactory()
        file_downloader_factory = FileDownloaderFactory.with_remote_files(fsf, config, [
            (first_fake_temp_file, db_test_with_default_filter_descr(db_default_option_filter).testable)
        ])
        importer_factory = ImporterCommandFactorySpy(config)
        service = FullRunService(file_system_factory=fsf, config=config, importer_command_factory=importer_factory, file_downloader_factory=file_downloader_factory)
        service.full_run()
        actual = first_filter(importer_factory)
        self.assertEquals(None if actual is None else actual.lower(), None if output_filter is None else output_filter.lower())


def first_filter(spy: ImporterCommandFactorySpy):
    return spy.commands()[0][0][2][K_FILTER]
