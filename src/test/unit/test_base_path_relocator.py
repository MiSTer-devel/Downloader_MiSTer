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

from downloader.base_path_relocator import RelocatorError
from downloader.other import empty_store
from test.fake_importer_command import ImporterCommand
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_file_system import FakeFileSystemFactory
from test.objects import db_test_with_file_a, store_test_with_file_a_descr, store_test_with_file, file_a, \
    empty_config, config_test


def media_fat_store():
    return store_test_with_file_a_descr()


def media_fat_store_with_system_file():
    return store_test_with_file(file_a, {'path': 'system'})


class TestBasePathRelocator(unittest.TestCase):

    def setUp(self) -> None:
        self.file_system_factory = FakeFileSystemFactory()
        self.media_fat_file_system = self.file_system_factory.create_for_base_path(config_test(base_path='/media/fat/'), '/media/fat/')
        self.media_usb0_file_system = self.file_system_factory.create_for_base_path(config_test(base_path='/media/usb0/'), '/media/usb0/')
        self.sut = BasePathRelocator(self.file_system_factory)

    def test_relocating_base_paths___with_empty_command___returns_empty_array(self):
        self.assertEqual([], self.sut.relocating_base_paths(ImporterCommand(empty_config())))

    def test_relocating_base_paths___with_command_containing_new_store___returns_empty_array(self):
        self.assertEqual([], self.sut.relocating_base_paths(command(empty_store(base_path='/media/fat/'), base_path='/media/fat/')))

    def test_relocating_base_paths___with_command_containing_old_store_with_matching_base_path___returns_empty_array(self):
        self.assertEqual([], self.sut.relocating_base_paths(command(media_fat_store(), base_path='/media/fat/')))

    def test_relocating_base_paths___with_command_containing_old_store_with_non_matching_base_path___returns_a_length_one_array(self):
        importer_command = command(media_fat_store_with_system_file(), base_path='/media/usb0/')
        self.assertEqual(1, len(self.sut.relocating_base_paths(importer_command)))

    def test_relocate_non_system_files___with_package_with_system_file_moved_from_fat_to_usb0___causes_system_file_to_stay_at_fat(self):
        self.media_fat_file_system.test_data.with_file_a()

        self.relocate_non_system_files_to_media_usb0(store=media_fat_store_with_system_file())

        self.assertFalse(self.media_usb0_file_system.is_file(file_a))
        self.assertTrue(self.media_fat_file_system.is_file(file_a))

    def test_relocate_non_system_files___on_buggy_filesystem___raises_error(self):
        self.media_fat_file_system.test_data.with_file_a()
        self.media_usb0_file_system.set_copy_buggy()

        self.assertRaises(RelocatorError, lambda: self.relocate_non_system_files_to_media_usb0(store=media_fat_store()))
        self.assertTrue(self.media_fat_file_system.is_file(file_a))
        self.assertFalse(self.media_usb0_file_system.is_file(file_a))

    def test_relocate_non_system_files___with_package_with_file_a_moved_from_fat_to_usb0___causes_file_a_to_move_to_usb0(self):
        self.media_fat_file_system.test_data.with_file_a()

        self.relocate_non_system_files_to_media_usb0(store=media_fat_store())

        self.assertFalse(self.media_fat_file_system.is_file(file_a))
        self.assertTrue(self.media_usb0_file_system.is_file(file_a))

    def test_relocate_non_system_files___with_package_with_file_a_moved_from_fat_to_usb0___but_file_a_not_in_file_system___does_nothing(self):
        self.relocate_non_system_files_to_media_usb0(store=media_fat_store())

        self.assertFalse(self.media_fat_file_system.is_file(file_a))
        self.assertFalse(self.media_usb0_file_system.is_file(file_a))

    def relocate_non_system_files_to_media_usb0(self, store):
        importer_command = command(store, base_path='/media/usb0/')

        packages = self.sut.relocating_base_paths(importer_command)
        self.sut.relocate_non_system_files(packages[0])


def command(input_store, base_path):
    importer_command = ImporterCommand(config_test(base_path=base_path))
    importer_command.add_db(db=db_test_with_file_a(), store=input_store, ini_description={})
    return importer_command
