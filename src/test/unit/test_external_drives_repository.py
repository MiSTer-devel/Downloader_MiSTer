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
from pathlib import Path

from downloader.constants import MEDIA_FAT_CIFS, MEDIA_USB0
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from test.fake_importer_implicit_inputs import FileSystemState
from downloader.logger import NoLogger
from test.fake_file_system_factory import FileSystemFactory


class TestExternalDrivesRepository(unittest.TestCase):
    def test_reads_proc_mounts___when_doesnt_exists___returns_no_drives(self):
        self.assertEqual((), sut(FileSystemFactory().create_for_system_scope()).connected_drives())

    def test_reads_proc_mounts___when_contains_file_with_media_fat_cifs_and_media_usb0___returns_media_fat_cifs_and_media_usb0(self):
        self.assertEqual((MEDIA_USB0, MEDIA_FAT_CIFS), sut(fs('test/unit/fixtures/proc_mounts_with_media_fat_cifs_and_media_usb0.txt')).connected_drives())

    def test_reads_proc_mounts___when_contains_invalid_file___returns_no_drives(self):
        self.assertEqual((), sut(fs('test/unit/fixtures/proc_mounts_invalid.txt')).connected_drives())


def sut(file_system):
    return ExternalDrivesRepositoryFactory().create(file_system, NoLogger())


def fs(proc_mounts_content):
    fs_state = FileSystemState(files={'/proc/mounts': {'content': Path(proc_mounts_content).read_text()}})
    return FileSystemFactory(fs_state).create_for_system_scope()
