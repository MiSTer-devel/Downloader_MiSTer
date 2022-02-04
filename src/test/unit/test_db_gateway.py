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
from test.fake_file_downloader import FileDownloader
from test.objects import db_test_descr, db_test
from test.fake_db_gateway import DbGateway
from test.fake_file_system import first_fake_temp_file, FileSystem
from test.factory_stub import FactoryStub

http_db_url = 'https://this_is_my_uri.json.zip'
fs_db_path = 'this_is_my_uri.json.zip'


class TestDbGateway(unittest.TestCase):
    def test_fetch_all___db_with_working_http_uri___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().testable}

        fs = FileSystem()
        factory = FactoryStub(FileDownloader(file_system=fs)).has(lambda fd: fd.test_data.brings_file(first_fake_temp_file, db_description))

        self.assertEqual(db_test_descr().testable, fetch_all(http_db_url, fs, factory))

    def test_fetch_all___db_with_fs_path___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().testable}

        fs = FileSystem()
        fs.test_data.with_file(fs_db_path, db_description)

        self.assertEqual(db_test_descr().testable, fetch_all(fs_db_path, fs))

    def test_fetch_all___db_with_wrong_downloaded_file___returns_none(self):
        self.assertEqual(None, fetch_all(http_db_url))

    def test_fetch_all___db_with_failing_http_uri___returns_none(self):
        factory = FactoryStub(FileDownloader()).has(lambda fd: fd.test_data.errors_at(first_fake_temp_file))
        self.assertEqual(None, fetch_all(http_db_url, factory=factory))


def fetch_all(db_url, fs=None, factory=None):
    dbs, errors = DbGateway(file_system=fs, file_downloader_factory=factory).fetch_all(test_db(db_url))
    if len(dbs) == 0:
        return None
    return dbs[0].testable


def test_db(db_uri):
    return {db_test: {'section': db_test, 'db_url': db_uri}}
