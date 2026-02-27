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

from downloader.config import default_config
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data
from test.objects import (
    file_psx_20250101_rbf, file_psx_20250202_rbf, file_nes_20250202_rbf, files_psx_20250101_rbf, files_psx_20250202_rbf,
    files_nes_20250101_rbf, files_nes_20250202_rbf, db_test_with_psx_20250101_rbf, db_test_with_psx_20250202_rbf,
    db_test_with_psx_20250202_and_nes_20250202_rbf, store_test_with_psx_20250101_rbf_descr,
    store_test_with_psx_20250202_rbf_descr, store_test_with_psx_20250101_and_nes_20250101_rbf_descr,
    store_test_with_psx_20250101_and_nes_20250202_rbf_descr
)

from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase


class TestOnlineImporterFileEntanglements(OnlineImporterTestBase):
    """
    Specification for file entanglement over successive database updates.

    File entanglement occurs when different file versions represent the same functional
    entity across successive database updates. When a newer version fails to download,
    the system must retain the older version to prevent breaking user functionality.

    Example: PSX_20250101.rbf and PSX_20250202.rbf are entangled - both represent the
    PSX core firmware at different points in time. If PSX_20250202.rbf download fails,
    PSX_20250101.rbf must be preserved to keep the PSX core working.
    """

    def test_download_entangled_rbf___when_old_version_installed_and_network_fails___keeps_old_version(self):
        store = store_test_with_psx_20250101_rbf_descr()
        sut = self.download_psx_20250202_db(
            store,
            fs(files=files_psx_20250101_rbf(), remote_failures={file_psx_20250202_rbf: 99})
        )

        self.assertEqual(store_test_with_psx_20250101_rbf_descr(), store)
        self.assertEqual(fs_data(files=files_psx_20250101_rbf()), sut.fs_data)
        self.assertReports(sut, installed=[], errors=[file_psx_20250202_rbf], save=False)

    def test_download_entangled_rbf___when_old_version_installed_and_network_succeeds___replaces_old_with_new(self):
        store = store_test_with_psx_20250101_rbf_descr()
        sut = self.download_psx_20250202_db(
            store,
            fs(files=files_psx_20250101_rbf())
        )

        self.assertEqual(store_test_with_psx_20250202_rbf_descr(), store)
        self.assertEqual(fs_data(files=files_psx_20250202_rbf()), sut.fs_data)
        self.assertReports(sut, installed=[file_psx_20250202_rbf])

    def test_download_entangled_rbf___when_old_version_in_store_but_not_on_fs_and_network_fails___installs_nothing(self):
        store = store_test_with_psx_20250101_rbf_descr()
        sut = self.download_psx_20250202_db(
            store,
            fs(remote_failures={file_psx_20250202_rbf: 99})
        )

        self.assertEqual(store_test_with_psx_20250101_rbf_descr(), store)
        self.assertEqual(fs_data(), sut.fs_data)
        self.assertReports(sut, installed=[], errors=[file_psx_20250202_rbf], save=False)

    def test_download_entangled_rbf___when_psx_fails_and_nes_succeeds___only_psx_coupling_applies(self):
        store = store_test_with_psx_20250101_and_nes_20250101_rbf_descr()
        sut = self.download_psx_20250101_and_nes_20250101_db(store, fs(
            files={**files_psx_20250101_rbf(), **files_nes_20250101_rbf()},
            remote_failures={file_psx_20250202_rbf: 99}
        ))

        self.assertEqual(store_test_with_psx_20250101_and_nes_20250202_rbf_descr(), store)
        self.assertEqual(fs_data(files={**files_psx_20250101_rbf(), **files_nes_20250202_rbf()}), sut.fs_data)
        self.assertReports(sut, installed=[file_nes_20250202_rbf], errors=[file_psx_20250202_rbf])

    def test_download_entangled_rbf___when_network_fails_then_succeeds_on_retry___replaces_old_with_new(self):
        store = store_test_with_psx_20250101_rbf_descr()
        sut = self.download_psx_20250202_db(
            store,
            fs(files=files_psx_20250101_rbf(), remote_failures={file_psx_20250202_rbf: 1})
        )

        self.assertEqual(store_test_with_psx_20250202_rbf_descr(), store)
        self.assertEqual(fs_data(files=files_psx_20250202_rbf()), sut.fs_data)
        self.assertReports(sut, installed=[file_psx_20250202_rbf])

    def test_download_entangled_rbf___when_old_version_has_wrong_hash_and_network_fails___keeps_corrupted_old_version(self):
        store = store_test_with_psx_20250101_rbf_descr()
        sut = self.download_psx_20250202_db(
            store,
            fs(files={file_psx_20250101_rbf: {'hash': 'corrupted_hash', 'size': 2915040}}, remote_failures={file_psx_20250202_rbf: 99})
        )

        self.assertEqual(store_test_with_psx_20250101_rbf_descr(), store)
        self.assertEqual(fs_data(files={file_psx_20250101_rbf: {'hash': 'corrupted_hash', 'size': 2915040}}), sut.fs_data)
        self.assertReports(sut, installed=[], errors=[file_psx_20250202_rbf], save=False)

    def download_psx_20250101_db(self, store, fs_inputs): return self._download_db(db_test_with_psx_20250101_rbf(), store, fs_inputs)
    def download_psx_20250202_db(self, store, fs_inputs): return self._download_db(db_test_with_psx_20250202_rbf(), store, fs_inputs)
    def download_psx_20250101_and_nes_20250101_db(self, store, fs_inputs): return self._download_db(db_test_with_psx_20250202_and_nes_20250202_rbf(), store, fs_inputs)



def fs(files=None, folders=None, remote_failures=None):
    return ImporterImplicitInputs(
        files=files or {},
        folders=folders or [],
        remote_failures=remote_failures or {},
        config=default_config()
    )