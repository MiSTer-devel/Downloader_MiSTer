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

from downloader.config import default_config
from downloader.free_space_reservation import Partition
from downloader.online_importer import InstallationBox
from downloader.path_package import PathPackage, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD
from test.fake_final_reporter import FinalReporter
from test.objects import db_entity


class TestFinalReporter(unittest.TestCase):

    def test_display_end_summary___with_all_branches___executes_without_error(self):
        box = InstallationBox()
        box.add_installed_db(db_entity(db_id='db1'), default_config(), 'hash1', 100)
        box.add_installed_db(db_entity(db_id='db2'), default_config(), 'hash2', 200)
        box.add_validated_file(make_path_pkg('file1.txt'), 'db1')
        box.add_validated_file(make_path_pkg('file2.txt'), 'db2')
        box.set_unused_filter_tags(['unused_tag1', 'unused_tag2'])
        box.add_failed_file('failed_file.txt')
        box.add_failed_db('db1')
        box.add_failed_folders(['failed_folder1', 'failed_folder2'])
        box.add_failed_zip('db1', 'failed_zip')
        box.add_skipped_updated_files([make_path_pkg('skipped1.txt'), make_path_pkg('skipped2.txt')], 'db1')
        box.add_full_partitions([(Partition(1000, 10, 512, '/media/fat'), 100), (Partition(2000, 20, 512, '/media/usb0'), 200)])
        box.set_old_pext_paths({'old_path1', 'old_path2'})

        FinalReporter().display_end_summary(box)

    def test_display_no_certs_msg___executes_without_error(self):
        FinalReporter().display_no_certs_msg()

    def test_display_network_problems_msg___executes_without_error(self):
        FinalReporter().display_network_problems_msg()

    def test_display_no_store_msg___executes_without_error(self):
        FinalReporter().display_no_store_msg()

    def test_display_file_error_failures___with_all_failure_types___executes_without_error(self):
        box = InstallationBox()
        box.add_failed_file('failed1.txt')
        box.add_failed_file('failed2.txt')
        box.add_failed_folders(['folder1', 'folder2'])
        box.add_failed_zip('db1', 'zip1')
        box.add_failed_zip('db2', 'zip2')
        box.add_failed_db('db1')
        box.add_failed_db('db2')

        FinalReporter().display_file_error_failures(box)


def make_path_pkg(rel_path):
    return PathPackage(
        rel_path=rel_path,
        drive='/media/fat',
        description={},
        ty=PATH_TYPE_FILE,
        kind=PATH_PACKAGE_KIND_STANDARD,
        pext_props=None
    )
