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

from downloader.constants import K_SECTION, K_DB_URL
from test.fake_importer_implicit_inputs import NetworkState
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.objects import db_test_descr, db_test
from test.fake_db_gateway import DbGateway
from test.fake_file_system_factory import first_fake_temp_file, FileSystemFactory

http_db_url = 'https://this_is_my_uri.json.zip'
fs_db_path = 'this_is_my_uri.json.zip'


class TestDbGateway(unittest.TestCase):
    def test_fetch_all___db_with_working_http_uri___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().testable}

        file_system_factory = FileSystemFactory()
        factory = FileDownloaderFactory(file_system_factory=file_system_factory, network_state=NetworkState(
            remote_files={first_fake_temp_file: db_description}))

        self.assertEqual(db_test_descr().testable, fetch_all(http_db_url, file_system_factory, factory))

    def test_fetch_all___db_with_fs_path___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().testable}

        file_system_factory = FileSystemFactory.from_state(files={fs_db_path: db_description})

        self.assertEqual(db_test_descr().testable, fetch_all(fs_db_path, file_system_factory))

    def test_fetch_all___db_with_wrong_downloaded_file___returns_none(self):
        self.assertEqual(None, fetch_all(http_db_url))

    def test_fetch_all___db_with_failing_http_uri___returns_none(self):
        factory = FileDownloaderFactory(network_state=NetworkState(storing_problems={first_fake_temp_file: 99}))
        self.assertEqual(None, fetch_all(http_db_url, factory=factory))


def fetch_all(db_url, file_system_factory=None, factory=None):
    dbs, errors = DbGateway(file_system_factory=file_system_factory, file_downloader_factory=factory).fetch_all(test_db(db_url))
    if len(dbs) == 0:
        return None
    return dbs[0].testable


def test_db(db_uri):
    return {db_test: {K_SECTION: db_test, K_DB_URL: db_uri}}
