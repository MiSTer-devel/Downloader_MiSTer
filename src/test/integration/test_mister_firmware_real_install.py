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

import os
import tempfile
from pathlib import Path

from downloader.constants import FILE_MiSTer, DISTRIBUTION_MISTER_DB_ID, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    FILE_MiSTer_old, FILE_MiSTer_new, FILE_downloader_storage_json, MEDIA_FAT
from downloader.job_system import JobFailPolicy
from downloader.local_store_wrapper import LocalStoreWrapper
from test.fake_store_migrator import StoreMigrator
from test.fake_file_system_factory import make_production_filesystem_factory
from test.fake_online_importer import OnlineImporter, StartJobPolicy
from test.objects import config_with, file_mister_descr, db_entity, store_descr
from test.unit.online_importer.online_importer_with_priority_storage_test_base import OnlineImporterWithPriorityStorageTestBase


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

        local_store = LocalStoreWrapper({
            "dbs": {DISTRIBUTION_MISTER_DB_ID: store_descr(base_path=base_path, files={FILE_MiSTer: file_mister_descr(hash_code=old_mister_hash)})},
            "db_fingerprints": {},
            "migration_version": StoreMigrator().latest_migration_version()
        })
        store_path = os.path.join(base_system_path, FILE_downloader_storage_json)
        file_system.make_dirs_parent(store_path)
        file_system.save_json(local_store.unwrap_local_store(), store_path)
        self.assertIsNone(sut.box())

        sut.add_db(db).download()

        self.assertNotEqual(new_mister_hash, old_mister_hash)
        actual_store = sut.box().local_store().store_by_id(DISTRIBUTION_MISTER_DB_ID).unwrap_store()
        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, base_path=base_path, files={FILE_MiSTer: file_mister_descr(hash_code=new_mister_hash)}), actual_store)
        self.assertReports(sut, [FILE_MiSTer], needs_reboot=True)

        self.assertEqual(new_mister_hash, file_system.hash(path_file_mister))
        self.assertEqual(old_mister_hash, file_system.hash(path_file_mister_old))

    def test_mister_update___when_swap_clobbers_binary_and_base_system_path_is_not_media_fat___restores_old_binary(self):
        # Regression: the MiSTer recovery in online_importer gates on the hardcoded
        # /media/fat/MiSTer (file_mister_present), but the binary actually lives at
        # <base_system_path>/MiSTer. When base_system_path != /media/fat (PC launcher,
        # relocated install, or this test) a failed swap that clobbers the binary is
        # silently skipped and MiSTer is left missing. Recovery should instead key off
        # the per-file `already_exists`, which tracks the real target path.
        self.assertFalse(Path(MEDIA_FAT, FILE_MiSTer).is_file(),
                         'precondition: the test host must not have a real /media/fat/MiSTer, '
                         'otherwise file_mister_present would mask the bug')

        base_path = self.base_path.name.lower()
        base_system_path = self.base_system_path.name.lower()

        old_mister_hash = '149603e6c03516362a8da23f624db945'
        new_mister_hash = '3de8f8b0dc94b8c2230fab9ec0ba0506'
        path_file_mister = str(Path(base_system_path).joinpath(FILE_MiSTer))

        config = config_with(storage_priority=STORAGE_PRIORITY_PREFER_EXTERNAL, base_system_path=base_system_path, base_path=base_path)
        db = db_entity(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr(hash_code=new_mister_hash)})

        sut, file_system = online_importer_fault_tolerant(config)
        file_system.write_file_contents(path_file_mister, 'old')
        self.assertEqual(old_mister_hash, file_system.hash(path_file_mister))

        local_store = LocalStoreWrapper({
            "dbs": {DISTRIBUTION_MISTER_DB_ID: store_descr(base_path=base_path, files={FILE_MiSTer: file_mister_descr(hash_code=old_mister_hash)})},
            "db_fingerprints": {},
            "migration_version": StoreMigrator().latest_migration_version()
        })
        store_path = os.path.join(base_system_path, FILE_downloader_storage_json)
        file_system.make_dirs_parent(store_path)
        file_system.save_json(local_store.unwrap_local_store(), store_path)

        # Simulate the "should never happen" botched atomic swap: renaming MiSTer.new onto
        # MiSTer destroys the live binary and then fails. By this point the swap has already
        # copied the old binary to .MiSTer.old, which is exactly what recovery must restore.
        # The recovery restore (.MiSTer.old -> MiSTer) is deliberately left untouched.
        fs = sut.file_system
        original_move = fs.move
        def botched_move(source, target, make_parent_target=True):
            if os.path.basename(source).lower() == FILE_MiSTer_new.lower() \
                    and os.path.basename(target).lower() == FILE_MiSTer.lower():
                fs.unlink(target, verbose=False)
                raise OSError('simulated botched rename of MiSTer.new -> MiSTer')
            return original_move(source, target, make_parent_target)
        fs.move = botched_move

        sut.add_db(db).download()

        # The update is correctly reported as failed...
        self.assertIn(FILE_MiSTer, sut.box().failed_files())

        # ...but the binary must NOT be left missing. Today recovery is skipped because
        # /media/fat/MiSTer does not exist here, so these assertions fail (the bug). Keying
        # recovery off `already_exists` restores the previous known-good binary instead.
        self.assertTrue(file_system.is_file(path_file_mister, use_cache=False),
                        'MiSTer binary was left missing after a failed swap: recovery is gated on /media/fat')
        self.assertEqual(old_mister_hash, file_system.hash(path_file_mister))


def online_importer(config):
    path_dictionary = {'asdf': 3}
    file_system_factory = make_production_filesystem_factory(config, path_dictionary=path_dictionary)
    return OnlineImporter(config=config, file_system_factory=file_system_factory), file_system_factory.create_for_config(config)


def online_importer_fault_tolerant(config):
    path_dictionary = {'asdf': 3}
    file_system_factory = make_production_filesystem_factory(config, path_dictionary=path_dictionary)
    sut = OnlineImporter(config=config, file_system_factory=file_system_factory, job_fail_policy=JobFailPolicy.FAULT_TOLERANT)
    return sut, file_system_factory.create_for_config(config)
