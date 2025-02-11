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
import os
import tempfile
import unittest
from pathlib import Path

from downloader.logger import FileLoggerDecorator
from test.fake_logger import NoLogger
from test.fake_external_drives_repository import ExternalDrivesRepositoryStub
from test.fake_file_system_factory import make_production_filesystem_factory
from test.fake_local_repository import LocalRepository
from test.objects import config_with


print_line = 'this is the print line'


class TestFileLogger(unittest.TestCase):

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_file_logger___after_being_initialized_and_finalized___generates_a_log_file_in_the_file_system(self):
        self.configure_and_initialize_file_logger()
        self.logger.finalize()
        self.assertTrue(os.path.isfile(self.local_repository.logfile_path))

    def test_file_logger___after_being_initialized_but_not_finalized___generates_no_log_file_in_file_system(self):
        self.configure_and_initialize_file_logger()
        self.assertFalse(os.path.isfile(self.local_repository.logfile_path))

    def test_initialized_file_logger___after_printing_and_then_finalizing___generates_file_containing_print_line(self):
        self.configure_and_initialize_file_logger()
        self.logger.print(print_line, end='')
        self.logger.finalize()
        self.assertEqual(print_line, Path(self.local_repository.logfile_path).read_text())

    def test_empty_finalized_file_logger___after_printing_line__genereates_empty_log(self):
        self.configure_and_initialize_file_logger()
        self.logger.finalize()
        self.logger.print(print_line, end='')
        self.assertNotEqual(print_line, Path(self.local_repository.logfile_path).read_text())

    def configure_and_initialize_file_logger(self):
        self.logger = FileLoggerDecorator(NoLogger())
        config = config_with(base_path=self.tempdir.name, base_system_path=self.tempdir.name)
        file_system = make_production_filesystem_factory(config=config).create_for_system_scope()
        self.local_repository = LocalRepository(config=config, file_system=file_system, external_drive_repository=ExternalDrivesRepositoryStub([self.tempdir.name]))
        self.logger.set_local_repository(self.local_repository)
