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

from downloader.constants import PathType
from test.objects import config_with
from test.fake_path_resolver import PathResolverFactory


base_path = '/standard'
base_system_path = '/system'
external_storage = 'off'


tmp_whatever = '/tmp/whatever'
normal_path_1 = 'normal/file'
normal_path_2 = 'other/file'

nt_normal_path = 'C:\\normal\\file'
nt_not_c_path = 'D:\\normal\\file'

storage_priority_normal_path = '|games/core/file'


def path_resolver(os_name=None, path_dictionary=None):
    return PathResolverFactory(os_name=os_name, path_dictionary=path_dictionary)\
        .create(config_with(base_path=base_path, base_system_path=base_system_path, storage_priority=external_storage), {})


class TestPathResolver(unittest.TestCase):
    def test_resolve_correct_paths___return_expected_base_paths(self):
        for n, (path, expected) in enumerate([
            (normal_path_1, None),
            (normal_path_2, None),
            (tmp_whatever, None)
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assertEqual(expected, path_resolver().resolve_file_path(path))

    def test_resolve_correct_system_paths___return_expected_base_paths(self):
        for n, (path, expected, system_paths) in enumerate([
            (normal_path_1, None, []),
            (normal_path_1, base_system_path, [normal_path_1]),
            (tmp_whatever, None, [tmp_whatever])
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assert_system_resolve(expected, path, system_paths)

    def test_resolve_correct_paths___writes_expected_path_dictionary(self):
        path_dictionary = {}
        sut = path_resolver(path_dictionary=path_dictionary)

        sut.add_system_path(normal_path_2)
        sut.resolve_file_path(normal_path_1)
        sut.resolve_file_path(normal_path_2)
        sut.resolve_file_path(tmp_whatever)
        sut.resolve_file_path(storage_priority_normal_path)

        self.assertEqual({
            normal_path_2: base_system_path,
        }, path_dictionary)


    def test_resolve_correct_nt_paths___return_expected_base_paths(self):
        for n, (path, expected, os_name) in enumerate([
            (nt_normal_path, None, ''),
            (nt_normal_path, None, 'nt'),
            (nt_not_c_path, None, 'nt'),
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assertEqual(expected, path_resolver(os_name=os_name).resolve_file_path(path))

    def test_resolve_storage_priorities(self):
        self.assertEqual(None, path_resolver().resolve_file_path(storage_priority_normal_path))

    # def test_system_paths_on_fs_1_and_2_created_by_same_factory___when_fs_1_adds_system_path_file_a___fs_2_download_target_path_returns_system_path_for_file_a(self):
    #     fs_1, fs_2 = self.fs_1_and_2_by_same_factory()
    #     fs_1.add_system_path(file_a)
    #
    #     self.assertEqual(file_a, fs_2.download_target_path(file_a))
    #
    # def test_system_paths_on_fs_1_and_2_created_by_same_factory___when_fs_1_adds_system_path_file_a___fs_2_and_fs_1_download_target_path_are_the_same_for_file_a(self):
    #     fs_1, fs_2 = self.fs_1_and_2_by_same_factory()
    #     fs_1.add_system_path(file_a)
    #
    #     self.assertEqual(fs_1.download_target_path(file_a), fs_2.download_target_path(file_a))
    #
    # def test_system_paths_on_fs_1_and_2_created_by_same_factory___when_no_system_path_is_added___fs_2_download_target_path_returns_base_path_for_file_a(self):
    #     fs_1, fs_2 = self.fs_1_and_2_by_same_factory()
    #     self.assertEqual(file_a, fs_2.download_target_path(file_a))
    #
    # def test_system_paths_on_fs_1_and_2_created_by_same_factory___when_fs_1_adds_system_path_file_a___fs_2_download_target_path_returns_base_path_for_file_b(self):
    #     fs_1, fs_2 = self.fs_1_and_2_by_same_factory()
    #     fs_1.add_system_path(file_a)
    #
    #     self.assertEqual(file_b, fs_2.download_target_path(file_b))


    def assert_system_resolve(self, expected, input, system_paths):
        this_sut = path_resolver()
        for path in system_paths:
            this_sut.add_system_path(path)
        self.assertEqual(expected, this_sut.resolve_file_path(input))
