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

from downloader.path_package import PathType
from test.fake_target_path_calculator import TargetPathCalculatorFactory
from test.objects import config_with


base_path = '/standard'
base_system_path = '/system'
external_storage = 'off'


tmp_whatever = '/tmp/whatever'
normal_path_1 = 'normal/file'
normal_path_2 = 'other/file'

storage_priority_normal_path = '|games/core/file'


def sut():
    config=config_with(base_path=base_path, base_system_path=base_system_path, storage_priority=external_storage)
    return TargetPathCalculatorFactory(config=config).target_paths_calculator(config=config)


class TestTargetPathCalculator(unittest.TestCase):
    def test_resolve_correct_paths___return_expected_base_paths(self):
        for n, (path, expected) in enumerate([
            (normal_path_1, base_path),
            (normal_path_2, base_path),
            (tmp_whatever, None)
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assertEqual(expected, sut().deduce_target_path(path, {}, PathType.FILE)[0].drive)

    def test_resolve_correct_system_paths___return_expected_base_paths(self):
        for n, (path, expected, system_paths) in enumerate([
            (normal_path_1, base_path, []),
            (normal_path_1, base_system_path, [normal_path_1]),
            (tmp_whatever, None, [tmp_whatever])
        ]):
            with self.subTest('%d %s' % (n, path)):
                self.assert_system_resolve(expected, path, system_paths)

    def test_resolve_storage_priorities(self):
        self.assertEqual(base_path, sut().deduce_target_path(storage_priority_normal_path, {}, PathType.FILE)[0].drive)

    def assert_system_resolve(self, expected, input, system_paths):
        this_sut = sut()
        description = {}
        for input in system_paths:
            description['path'] = 'system'
        self.assertEqual(expected, this_sut.deduce_target_path(input, description, PathType.FILE)[0].drive)
