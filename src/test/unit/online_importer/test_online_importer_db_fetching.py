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

from typing import Optional
import unittest

from downloader.constants import K_SECTION, K_DB_URL, MEDIA_FAT
from downloader.db_utils import DbSectionPackage
from downloader.jobs.worker_context import DownloaderWorkerFailPolicy
from test.fake_importer_implicit_inputs import NetworkState
from test.fake_local_store_wrapper import local_store_wrapper
from test.fake_online_importer import OnlineImporter
from test.objects import db_test_descr, db_test, empty_store
from test.fake_file_system_factory import FileSystemFactory

http_db_url = 'https://this_is_my_uri.json.zip'
fs_db_path = '/this_is_my_uri.json.zip'
db_info = 'db test'


class TestOnlineImporterDbFetching(unittest.TestCase):
    def test_fetch_all___db_with_working_http_uri___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().extract_props()}
        self.assertEqual(db_test_descr().extract_props(), fetch_all(http_db_url, network_state=NetworkState(remote_files={http_db_url: db_description})))

    def test_fetch_all___db_with_fs_path___returns_expected_db(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().extract_props()}

        file_system_factory = FileSystemFactory.from_state(files={fs_db_path: db_description})

        self.assertEqual(db_test_descr().extract_props(), fetch_all(fs_db_path, file_system_factory))

    def test_fetch_all___db_with_wrong_downloaded_file___returns_none(self):
        self.assertEqual(None, fetch_all(http_db_url, fail=DownloaderWorkerFailPolicy.FAULT_TOLERANT))

    def test_fetch_all___db_with_failing_http_uri___returns_none(self):
        self.assertEqual(None, fetch_all(http_db_url, network_state=NetworkState(storing_problems={http_db_url: 99})))

1
def fetch_all(db_url: str, file_system_factory: Optional[FileSystemFactory] = None, network_state: Optional[NetworkState] = None, fail: Optional[DownloaderWorkerFailPolicy] = None):
    file_system_factory = file_system_factory or FileSystemFactory()
    sut = OnlineImporter(file_system_factory=file_system_factory, network_state=network_state, start_on_db_processing=False, fail_policy=fail)
    local_store = local_store_wrapper({db_test: empty_store(MEDIA_FAT)})
    db_pkg = DbSectionPackage(
        db_id=db_test,
        section={'db_url': db_url},
        store=local_store.store_by_id(db_test),
    )
    sut.set_local_store(local_store)
    sut.download_dbs_contents([db_pkg], False)
    dbs = sut.box().installed_dbs()
    if len(dbs) == 0:
        return None
    return dbs[0].extract_props()

def test_db(db_uri):
    return {db_test: {K_SECTION: db_test, K_DB_URL: db_uri}}
