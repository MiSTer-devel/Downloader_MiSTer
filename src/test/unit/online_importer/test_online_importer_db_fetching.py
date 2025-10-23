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

from downloader.constants import K_SECTION, K_DB_URL, FILE_downloader_storage_json
from downloader.db_utils import DbSectionPackage
from downloader.fail_policy import FailPolicy
from downloader.job_system import JobFailPolicy
from downloader.jobs.abort_worker import AbortJob
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.load_local_store_job import LoadLocalStoreJob
from downloader.jobs.load_local_store_sigs_job import LoadLocalStoreSigsJob
from downloader.jobs.open_db_job import OpenDbJob
from test.fake_importer_implicit_inputs import NetworkState
from test.fake_online_importer import OnlineImporter
from test.objects import db_test_descr, db_test, media_usb0
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
        self.assertEqual(None, fetch_all(http_db_url, fail=FailPolicy.FAULT_TOLERANT))

    def test_fetch_all___db_with_failing_http_uri___returns_none(self):
        self.assertEqual(None, fetch_all(http_db_url, fail=FailPolicy.FAULT_TOLERANT, network_state=NetworkState(storing_problems={http_db_url: 99})))

    def test_load_store_job___always_fails___job_system_gets_ongoing_jobs_cancelled(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().extract_props()}
        file_system_factory = FileSystemFactory.from_state(files={
            fs_db_path: db_description,
            media_usb0(FILE_downloader_storage_json): {'hash': 'ignore', 'unzipped_json': {}},
        })
        file_system_factory.set_read_error()

        sut = OnlineImporter(
            file_system_factory=file_system_factory,
            network_state=NetworkState(remote_files={http_db_url: db_description}),
            start_on_db_processing=False,
            job_fail_policy=JobFailPolicy.FAULT_TOLERANT
        )

        db_pkg = DbSectionPackage(
            db_id=db_test,
            section={'db_url': http_db_url, 'section': db_test},
        )
        sut.download_dbs_contents([db_pkg])

        self.assertTrue(sut.job_system.are_jobs_cancelled())
        self.assertEqual({
            "job_started": {FetchDataJob.__name__: 1, LoadLocalStoreSigsJob.__name__: 1, LoadLocalStoreJob.__name__: 4, AbortJob.__name__: 1, OpenDbJob.__name__: 1},
            "job_completed": {AbortJob.__name__: 1, FetchDataJob.__name__: 1, LoadLocalStoreSigsJob.__name__: 1},
            "job_retried": {LoadLocalStoreJob.__name__: 4, OpenDbJob.__name__: 1},
            "job_cancelled": {FetchDataJob.__name__: 1}
        }, sut.jobs_tracks())

def fetch_all(db_url: str, file_system_factory: Optional[FileSystemFactory] = None, network_state: Optional[NetworkState] = None, fail: Optional[FailPolicy] = None, job_fail: Optional[JobFailPolicy] = None):
    file_system_factory = file_system_factory or FileSystemFactory()
    sut = OnlineImporter(file_system_factory=file_system_factory, network_state=network_state, start_on_db_processing=False, fail_policy=fail, job_fail_policy=job_fail)
    db_pkg = DbSectionPackage(
        db_id=db_test,
        section={'db_url': db_url, 'section': db_test},
    )
    sut.download_dbs_contents([db_pkg])
    dbs = sut.box().installed_dbs()
    if len(dbs) == 0:
        return None
    return dbs[0].extract_props()

def test_db(db_uri):
    return {db_test: {K_SECTION: db_test, K_DB_URL: db_uri}}
