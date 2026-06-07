# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.jobs.process_db_index_worker import ProcessIndexCtx, create_fetch_jobs
from downloader.path_package import PATH_PACKAGE_KIND_STANDARD, PATH_TYPE_FILE, PathPackage
from test.fake_logger import NoLogger
from test.fake_update_output import SpyUpdateOutput


class TestProcessDbIndexWorkerOutput(unittest.TestCase):

    def test_create_fetch_jobs___default___reports_total_size(self):
        update_output = SpyUpdateOutput()

        jobs = create_fetch_jobs(
            ctx(update_output),
            'db1',
            [pkg('folder/file1.txt', 10), pkg('folder/file2.txt', 20)],
            [],
            set(),
            'https://example.com/files'
        )

        self.assertEqual(2, len(jobs))
        self.assertEqual([('db1', 30, 2, 'db', '')], update_output.database_size_added_calls)

    def test_create_fetch_jobs___without_size_reporting___does_not_report_total_size(self):
        update_output = SpyUpdateOutput()

        jobs = create_fetch_jobs(
            ctx(update_output),
            'db1',
            [pkg('folder/file1.txt', 10), pkg('folder/file2.txt', 20)],
            [],
            set(),
            'https://example.com/files',
            size_report_scope='zip',
            zip_id='zip1',
            should_report_size=False
        )

        self.assertEqual(2, len(jobs))
        self.assertEqual([], update_output.database_size_added_calls)


def ctx(update_output):
    return ProcessIndexCtx(
        fail_ctx=NoFailCtx(),
        file_system=NoFileSystem(),
        logger=NoLogger(),
        installation_report=None,
        file_filter_factory=None,
        target_paths_calculator_factory=None,
        file_download_session_logger=None,
        free_space_reservation=None,
        update_output=update_output,
    )


def pkg(rel_path, size):
    return PathPackage(
        rel_path=rel_path,
        drive=None,
        description={'hash': 'abc', 'size': size},
        ty=PATH_TYPE_FILE,
        kind=PATH_PACKAGE_KIND_STANDARD,
        pext_props=None
    )


class NoFailCtx:
    def swallow_error(self, exception):
        raise exception


class NoFileSystem:
    def make_dirs(self, path):
        raise AssertionError('make_dirs should not be called in this test')
