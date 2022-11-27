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
import tempfile
from pathlib import Path

from downloader.constants import FILE_MiSTer, DISTRIBUTION_MISTER_DB_ID, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    FILE_MiSTer_old
from test.fake_file_system_factory import make_production_filesystem_factory
from test.fake_path_resolver import PathResolverFactory
from test.fake_online_importer import OnlineImporter
from test.objects import config_with, file_mister_descr, db_entity, store_descr
from test.unit.online_importer_with_priority_storage_test_base import OnlineImporterWithPriorityStorageTestBase


class TestMiSTerFirmwareRealInstall(OnlineImporterWithPriorityStorageTestBase):
    def setUp(self) -> None:
        self.base_system_path = tempfile.TemporaryDirectory()
        self.base_path = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.base_system_path.cleanup()
        self.base_path.cleanup()

    def test_mister_download___with_crosslink_conditions___installs_mister_file(self):
        base_path = self.base_path.name.lower()
        base_system_path = self.base_system_path.name.lower()

        old_mister_hash = '149603e6c03516362a8da23f624db945'
        new_mister_hash = '3de8f8b0dc94b8c2230fab9ec0ba0506'
        path_file_mister = str(Path(base_system_path).joinpath(FILE_MiSTer))
        path_file_mister_old = str(Path(base_system_path).joinpath(FILE_MiSTer_old))

        config = config_with(storage_priority=STORAGE_PRIORITY_PREFER_EXTERNAL, base_system_path=base_system_path, base_path=base_path)

        db = db_entity(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr(hash_code=new_mister_hash)})

        sut, file_system = online_importer(config)
        file_system.write_file_contents(path_file_mister, 'old')
        file_system.write_file_contents(path_file_mister_old, 'very very old')
        self.assertEqual(old_mister_hash, file_system.hash(path_file_mister))
        self.assertEqual('c70c3e2ebd6dbde780ecd2d1df7d8440', file_system.hash(path_file_mister_old))

        actual_store = store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, base_path=base_path, files={FILE_MiSTer: file_mister_descr(hash_code=old_mister_hash)})

        sut.add_db(db, actual_store).download(False)

        self.assertNotEqual(new_mister_hash, old_mister_hash)
        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, base_path=base_path, files={FILE_MiSTer: file_mister_descr(hash_code=new_mister_hash)}), actual_store)
        self.assertReports(sut, [FILE_MiSTer], reboot=True)

        self.assertEqual(new_mister_hash, file_system.hash(path_file_mister))
        self.assertEqual(old_mister_hash, file_system.hash(path_file_mister_old))

def online_importer(config):
    path_dictionary = {'asdf': 3}
    file_system_factory = make_production_filesystem_factory(config, path_dictionary=path_dictionary)
    path_resolver_factory = PathResolverFactory(file_system_factory=file_system_factory, path_dictionary=path_dictionary)
    return OnlineImporter(config=config, file_system_factory=file_system_factory, path_resolver_factory=path_resolver_factory, path_dictionary=path_dictionary), file_system_factory.create_for_config(config)
