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

from test.fake_file_system_factory import FileSystemFactory
from test.objects import file_a, db_test, db_test_descr, media_fat
from test.fake_online_importer import OnlineImporter, StartJobPolicy
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from test.fake_importer_implicit_inputs import NetworkState
from downloader.db_options import DbOptions
from downloader.db_utils import DbSectionPackage

http_db_url = 'https://this_is_my_uri.json.zip'
fs_db_path = '/this_is_my_uri.json.zip'
abs_store_replica = '/wtf.json'

class TestOnlineImporterWithStoreReplica(OnlineImporterTestBase):

    def test_download_dbs_contents___on_new_db_with_abs_store_replica_wtf___returns_updated_store_with_replica_wtf(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().extract_props()}
        file_system_factory = FileSystemFactory.from_state(files={
            file_a: {'hash': 'does_not_match'},
            fs_db_path: db_description,
        })
        sut = OnlineImporter(file_system_factory=file_system_factory, network_state=NetworkState(remote_files={http_db_url: db_description}), start_job_policy=StartJobPolicy.FetchDb)
        db_pkg = DbSectionPackage(
            db_id=db_test,
            section={'db_url': http_db_url, 'section': db_test, 'options': DbOptions({'store_replica': abs_store_replica})},
        )
        box, ex = sut.download_dbs_contents([db_pkg])
        self.assertIsNone(ex)
        self.assertIsNotNone(box)
        self.assertTrue(box.local_store().needs_save())
        self.assertEqual(expected_store(), box.local_store().unwrap_local_store())
        self.assertEqual(expected_fs(), sut.fs_data)
        self.assertEqual({db_test: abs_store_replica}, box.local_store().replicas())

    def test_download_dbs_contents___on_new_db_without_store_replicas___returns_updated_store_but_no_replicas(self):
        db_description = {'hash': 'ignore', 'unzipped_json': db_test_descr().extract_props()}
        file_system_factory = FileSystemFactory.from_state(files={
            file_a: {'hash': 'does_not_match'},
            fs_db_path: db_description,
        })
        sut = OnlineImporter(file_system_factory=file_system_factory, network_state=NetworkState(remote_files={http_db_url: db_description}), start_job_policy=StartJobPolicy.FetchDb)
        db_pkg = DbSectionPackage(
            db_id=db_test,
            section={'db_url': http_db_url, 'section': db_test},
        )
        box, ex = sut.download_dbs_contents([db_pkg])
        self.assertIsNone(ex)
        self.assertIsNotNone(box)
        self.assertEqual(expected_store(), box.local_store().unwrap_local_store())
        self.assertTrue(box.local_store().needs_save())
        self.assertEqual(expected_fs(), sut.fs_data)
        self.assertEqual({}, box.local_store().replicas())


def expected_fs(): return {
    'files': {
        media_fat(file_a).lower(): {'hash': 'does_not_match', 'size': 1},
        fs_db_path: {'hash': 'ignore', 'size': 1}},
    'folders': {}
}

def expected_store(): return {
    'db_fingerprints': {
        'test': {
            'filter': '',
            'hash': 'ignore',
            'size': 1,
            'timestamp': 0
        }
    },
    'dbs': {
        'test': {
            'base_path': '/media/fat',
            'files': {},
            'folders': {},
            'zips': {}
        }
    },
    'internal': True,
    'migration_version': 12
}