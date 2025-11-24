# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.config import FileChecking
from downloader.constants import FILE_CHECKING_SPACE_CHECK_TOLERANCE, MEDIA_FAT, \
    FILE_downloader_previous_free_space_json, \
    FILE_downloader_last_successful_run, MEDIA_USB0, MEDIA_USB1, FILE_downloader_storage_json
from test.fake_file_checking_mode_resolver import FileCheckingModeResolver
from test.fake_file_system_factory import FileSystemFactory

one_mb = 1000000
two_mb = 2000000
five_mb = 5000000
half_mb = 500000
small_increase = 1000


class TestFileCheckingModeResolver(unittest.TestCase):

    def test_calc_file_checking_changes___when_file_checking_not_balanced___returns_none(self):
        for file_checking_value in [
            FileChecking.FASTEST,
            FileChecking.EXHAUSTIVE,
            FileChecking.VERIFY_INTEGRITY,
        ]:
            with self.subTest(file_checking=file_checking_value):
                self.assertIsNone(file_checking().calc_file_checking_changes(file_checking_value))

    def test_calc_file_checking_changes___when_last_successful_run_missing___returns_verify_integrity(self):
        for file_checking_value in [
            FileChecking.FASTEST,
            FileChecking.BALANCED,
            FileChecking.EXHAUSTIVE,
            FileChecking.VERIFY_INTEGRITY,
        ]:
            with self.subTest(file_checking=file_checking_value):
                self.assertEqual(FileChecking.VERIFY_INTEGRITY, file_checking(has_last_run=False).calc_file_checking_changes(file_checking_value))

    def test_calc_file_checking_changes___when_last_successful_run_and_store_are_missing___returns_none(self):
        for file_checking_value in [
            FileChecking.FASTEST,
            FileChecking.EXHAUSTIVE,
            FileChecking.VERIFY_INTEGRITY,
        ]:
            with self.subTest(file_checking=file_checking_value):
                self.assertEqual(None, file_checking(has_last_run=False, has_store=False).calc_file_checking_changes(file_checking_value))

    def test_calc_file_checking_changes___when_media_fat_missing_from_previous_spaces___returns_exhaustive(self):
        sut = file_checking(previous_free={MEDIA_USB0: one_mb}, actual_free={MEDIA_FAT: one_mb})
        self.assertEqual(FileChecking.EXHAUSTIVE, sut.calc_file_checking_changes(FileChecking.BALANCED))

    def test_calc_file_checking_changes___when_media_fat_missing_from_actual_spaces___returns_exhaustive(self):
        sut = file_checking(previous_free={MEDIA_FAT: one_mb}, actual_free={MEDIA_USB0: one_mb})
        self.assertEqual(FileChecking.EXHAUSTIVE, sut.calc_file_checking_changes(FileChecking.BALANCED))

    def test_calc_file_checking_changes___when_free_space_increased_over_tolerance___returns_exhaustive(self):
        for prev_free, current_free in [
            (one_mb, one_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE + small_increase),
            (one_mb, five_mb),
            (0, five_mb),
            (five_mb, five_mb * 1000)
        ]:
            with self.subTest(prev_free=prev_free, current_free=current_free):
                sut = file_checking(previous_free={MEDIA_FAT: prev_free}, actual_free={MEDIA_FAT: current_free})
                self.assertEqual(FileChecking.EXHAUSTIVE, sut.calc_file_checking_changes(FileChecking.BALANCED))

    def test_calc_file_checking_changes___when_free_space_stable___returns_fastest(self):
        for prev_free, current_free in [
            (one_mb, one_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE),
            (one_mb, one_mb),
            (five_mb, one_mb),
            (0, 0),
        ]:
            with self.subTest(prev_free=prev_free, current_free=current_free):
                sut = file_checking(previous_free={MEDIA_FAT: prev_free}, actual_free={MEDIA_FAT: current_free})
                self.assertEqual(FileChecking.FASTEST, sut.calc_file_checking_changes(FileChecking.BALANCED))

    def test_calc_file_checking_changes___when_multiple_partitions_and_one_increased___returns_exhaustive(self):
        for prev, current in [
            ({MEDIA_FAT: one_mb, MEDIA_USB0: two_mb}, {MEDIA_FAT: one_mb + small_increase, MEDIA_USB0: two_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE + small_increase}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: two_mb}, {MEDIA_FAT: one_mb, MEDIA_USB0: two_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE + small_increase}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: 0}, {MEDIA_FAT: one_mb, MEDIA_USB0: five_mb}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: one_mb, MEDIA_USB1: one_mb}, {MEDIA_FAT: one_mb, MEDIA_USB0: one_mb, MEDIA_USB1: one_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE + small_increase}),
            ({MEDIA_FAT: one_mb, MEDIA_USB1: one_mb}, {MEDIA_FAT: one_mb, MEDIA_USB0: one_mb, MEDIA_USB1: one_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE + small_increase})
        ]:
            with self.subTest(prev=prev, current=current):
                sut = file_checking(previous_free=prev, actual_free=current)
                self.assertEqual(FileChecking.EXHAUSTIVE, sut.calc_file_checking_changes(FileChecking.BALANCED))

    def test_calc_file_checking_changes___when_new_partition_appears___skips_it_and_returns_fastest(self):
        for prev, current in [
            ({MEDIA_FAT: one_mb, MEDIA_USB0: two_mb}, {MEDIA_FAT: one_mb + small_increase, MEDIA_USB0: two_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: two_mb}, {MEDIA_FAT: one_mb, MEDIA_USB0: two_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: 0}, {MEDIA_FAT: one_mb, MEDIA_USB0: 0}),
            ({MEDIA_FAT: one_mb, MEDIA_USB0: 0}, {MEDIA_FAT: one_mb + FILE_CHECKING_SPACE_CHECK_TOLERANCE, MEDIA_USB0: 0}),
        ]:
            with self.subTest(prev=prev, current=current):
                sut = file_checking(previous_free=prev, actual_free=current)
                self.assertEqual(FileChecking.FASTEST, sut.calc_file_checking_changes(FileChecking.BALANCED))


def file_checking(previous_free=None, actual_free=None, has_last_run=True, has_store=True):
    files = {}
    if has_store:
        files[f'{MEDIA_FAT}/{FILE_downloader_storage_json}'] = {}
    if has_last_run:
        files[f'{MEDIA_FAT}/{FILE_downloader_last_successful_run % ""}'] = {}
    if previous_free is not None:
        files[f'{MEDIA_FAT}/{FILE_downloader_previous_free_space_json}'] = {'json': previous_free}

    fs_factory = FileSystemFactory.from_state(files=files)
    fake_fs = fs_factory.create_for_system_scope()
    if actual_free is not None:
        fake_fs.set_free_spaces(actual_free)
    return FileCheckingModeResolver(file_system=fake_fs)
