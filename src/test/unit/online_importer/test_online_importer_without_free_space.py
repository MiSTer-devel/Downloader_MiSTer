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

from typing import Dict, Any

from downloader.config import default_config
from downloader.constants import MEDIA_FAT, STORAGE_PRIORITY_PREFER_EXTERNAL, MEDIA_USB1, DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB, DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB, STORAGE_PRIORITY_PREFER_SD
from downloader.free_space_reservation import LinuxFreeSpaceReservation, Partition, file_size_on_disk, partition_min_space
from test.fake_logger import NoLogger
from test.fake_file_system_factory import fs_data
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.objects import file_a, folder_a, db_test_with_file_a, empty_test_store, store_with_folders, store_test_with_file_a_descr, file_a_descr, config_with, file_size_a, \
    db_test_with_file_b, db_test_with_file_c, file_c, file_b, files_a, files_b, files_c, folder_c, folder_b, store_test_with_file_b_descr, store_test_with_file_c_descr, \
    file_size_b, file_size_c, db_smb1, db_sonic, folder_games_nes, folder_games, folder_games_md, file_nes_smb1, file_md_sonic, file_size_sonic, file_size_smb1, \
    media_usb1, media_fat, db_test_descr, db_test_with_file_d, file_d, file_size_d
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from test.unit.online_importer.online_importer_with_priority_storage_test_base import fs_files_smb1_on_usb1, fs_files_sonic_on_usb1, store_smb1_on_usb1, store_sonic_on_usb1, \
    store_sonic_on_usb1_but_just_folders, store_smb1_on_usb1_but_just_folders
from test.zip_objects import cheats_folder_id, cheats_folder_zip_desc, zipped_files_from_cheats_folder, summary_json_from_cheats_folder, store_with_unzipped_cheats, cheats_folder_folders, \
    cheats_folder_nes_file_path, cheats_folder_sms_file_path, cheats_folder_nes_file_size, cheats_folder_sms_file_size


class TestOnlineImporterWithoutFreeSpace(OnlineImporterTestBase):
    # @TODO: Right now the "free" expected value is NOT the final space value on the disk, but what would have been if the failed files were allocated.
    # I don't think this makes sense anymore, but needs to be changed in a later release. Because right now I prefer not to break the contracts anymore
    # than I had to do by not saving failed stores.

    def setUp(self) -> None:
        self.mb600 = 1024 * 1024 * 600
        self.size_a = file_size_on_disk(file_size_a, 32)
        self.size_b = file_size_on_disk(file_size_b, 32)
        self.size_c = file_size_on_disk(file_size_c, 32)
        self.size_d = file_size_on_disk(file_size_d, 32)
        self.size_smb1 = file_size_on_disk(file_size_smb1, 32)
        self.size_sonic = file_size_on_disk(file_size_sonic, 32)
        self.size_nes_cheat = file_size_on_disk(cheats_folder_nes_file_size, 32)
        self.size_sms_cheat = file_size_on_disk(cheats_folder_sms_file_size, 32)

    def test_file_size_on_disk(self):
        self.assertEqual(32, file_size_on_disk(32, 32))
        self.assertEqual(64, file_size_on_disk(33, 32))
        self.assertEqual(33, file_size_on_disk(33, 1))

    def test_partition_min_space(self):
        self.assertEqual(DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB, partition_min_space(default_config(), MEDIA_FAT))
        self.assertEqual(DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB, partition_min_space(default_config(), MEDIA_USB1))

    def test_download_db_file_a___without_enough_space___reports_error_and_full_partition_and_doesnt_save(self):
        sut, free, stores = self.download_db_file_a({MEDIA_FAT: Partition(1000, min_space=0, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={}, folders=[]),
            "stores": [empty_test_store()],
            "errors": [file_a],
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: 1000 - self.size_a},
            "save": False
        }, sut, stores, free=free)

    def test_download_db_file_a___without_enough_space_but_the_file_already_exists_somehow___reports_no_error_and_doesnt_save(self):
        sut, free, stores = self.download_db_file_a(
            {MEDIA_FAT: Partition(1000, min_space=0, block_size=32)},
            input_stores=[store_test_with_file_a_descr()], with_fs=fs(files={file_a: file_a_descr()})
        )
        self.assertSystem({
            "fs": fs_data(files={file_a: file_a_descr()}, folders=[folder_a]),
            "stores": [store_test_with_file_a_descr()],
            "errors": [],
            "full_partitions": [],
            "free": {MEDIA_FAT: 1000},
            "save": False
        }, sut, stores, free=free)

    def test_download_db_file_a___on_a_second_run_without_enough_space___reports_error_and_full_partition_and_doesnt_save(self):
        sut, free, stores = self.download_db_file_a({MEDIA_FAT: Partition(1000, min_space=0, block_size=32)},
                                                    input_stores=[store_with_folders([folder_a])],
                                                    with_fs=fs(folders=[folder_a]))
        self.assertSystem({
            "fs": fs_data(files={}, folders=[folder_a]),
            "stores": [store_with_folders([folder_a])],
            "errors": [file_a],
            "save": False,
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: 1000 - self.size_a}
        }, sut, stores, free=free)

    def test_download_db_file_a___with_tight_free_space___fills_store_with_that_file(self):
        sut, free, stores = self.download_db_file_a({MEDIA_FAT: Partition(self.mb600, min_space=597, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={file_a: file_a_descr()}, folders=[folder_a]),
            "stores": [store_test_with_file_a_descr()],
            "ok": [file_a],
            "free": {MEDIA_FAT: self.mb600 - self.size_a}
        }, sut, stores, free=free)

    def test_download_db_file_a___with_too_high_free_space___reports_error_and_full_partition_and_doesnt_save(self):
        sut, free, stores = self.download_db_file_a({MEDIA_FAT: Partition(self.mb600, min_space=598, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={}, folders=[]),
            "stores": [empty_test_store()],
            "errors": [file_a],
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: self.mb600 - self.size_a},
            "save": False
        }, sut, stores, free=free)

    def download_db_file_a(self, partitions: Dict[str, Any], input_stores=None, with_fs=None):
        return self._download_dbs(
            fs() if with_fs is None else with_fs,
            [db_test_with_file_a()],
            partitions, input_stores=input_stores
        )

    def test_download_three_dbs___with_tight_free_space___fills_store_with_three_files(self):
        sut, free, stores = self.download_three_dbs({MEDIA_FAT: Partition(self.mb600, min_space=591, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={**files_a(), **files_b(), **files_c()}, folders=[folder_a, folder_b, folder_c]),
            "stores": [store_test_with_file_a_descr(), store_test_with_file_b_descr(), store_test_with_file_c_descr()],
            "ok": [file_a, file_b, file_c],
            "free": {MEDIA_FAT: self.mb600 - self.size_a - self.size_b - self.size_c}
        }, sut, stores, free=free)

    def test_download_three_dbs___with_enough_free_space_for_two_out_of_tree_dbs___reports_error_for_last_one_and_full_partition(self):
        sut, free, stores = self.download_three_dbs({MEDIA_FAT: Partition(self.mb600, min_space=592, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={**files_a(), **files_b()}, folders=[folder_a, folder_b]),
            "stores": [store_test_with_file_a_descr(), store_test_with_file_b_descr(), empty_test_store()],
            "ok": [file_a, file_b],
            "errors": [file_c],
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: self.mb600 - self.size_a - self.size_b - self.size_c}
        }, sut, stores, free=free)

    def download_three_dbs(self, partitions: Dict[str, Any]):
        return self._download_dbs(
            fs(),
            [db_test_with_file_a(db_id='1'), db_test_with_file_b(db_id='2'), db_test_with_file_c(db_id='3')],
            partitions
        )

    def test_download_four_dbs___with_enough_free_space_for_two_out_of_four_dbs___reports_error_for_last_two_and_full_partition(self):
        sut, free, stores = self.download_four_dbs({MEDIA_FAT: Partition(self.mb600, min_space=592, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={**files_a(), **files_b()}, folders=[folder_a, folder_b]),
            "stores": [store_test_with_file_a_descr(), store_test_with_file_b_descr(), empty_test_store(), empty_test_store()],
            "ok": [file_a, file_b],
            "errors": [file_c, file_d],
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: self.mb600 - self.size_a - self.size_b - self.size_c - self.size_d}
        }, sut, stores, free=free)

    def download_four_dbs(self, partitions: Dict[str, Any]):
        return self._download_dbs(
            fs(),
            [db_test_with_file_a(db_id='1'), db_test_with_file_b(db_id='2'), db_test_with_file_c(db_id='3'), db_test_with_file_d(db_id='4')],
            partitions
        )

    def test_download_three_dbs_with_external_priority_files___with_enough_free_space_on_fat_but_not_on_usb1___fills_fat_and_reports_error_for_usb1(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(self.mb600, min_space=595, block_size=32),
            MEDIA_USB1: Partition(int(self.mb600 /2), min_space=595, block_size=32)
        })
        self.assertSystem({
            "fs": fs_data(files={**files_a()}, folders=[folder_a, folder_games, media_usb1(folder_games)]),
            "stores": [store_test_with_file_a_descr(), empty_test_store(), empty_test_store()],
            "ok": [file_a],
            "errors": [file_nes_smb1, file_md_sonic],
            "full_partitions": [MEDIA_USB1],
            "free": {MEDIA_FAT: self.mb600 - self.size_a, MEDIA_USB1: int(self.mb600 /2) - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def test_download_three_dbs_with_external_priority_files___with_enough_free_space_on_fat_but_only_partially_on_usb1___fills_fat_and_just_fitting_db_on_usb1_but_reports_error_for_second_db_on_usb1(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(self.mb600, min_space=595, block_size=32),
            MEDIA_USB1: Partition(self.mb600, min_space=595, block_size=32)
        })
        self.assertSystem({
            "fs": fs_data(files={**files_a(), **fs_files_smb1_on_usb1()}, folders=[folder_a, folder_games, media_usb1(folder_games), media_usb1(folder_games_nes)]),
            "stores": [store_test_with_file_a_descr(), store_smb1_on_usb1(), empty_test_store()],
            "ok": [file_a, file_nes_smb1],
            "errors": [file_md_sonic],
            "full_partitions": [MEDIA_USB1],
            "free": {MEDIA_FAT: self.mb600 - self.size_a, MEDIA_USB1: self.mb600 - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def test_download_three_dbs_with_external_priority_files___with_enough_free_space_on_usb1_but_not_on_fat___fills_usb1_and_reports_error_for_fat(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(int(self.mb600 / 2), min_space=512, block_size=32),
            MEDIA_USB1: Partition(self.mb600, min_space=512, block_size=32)
        })
        self.assertSystem({
            "fs": fs_data(
                files={**fs_files_smb1_on_usb1(), **fs_files_sonic_on_usb1()},
                folders=[folder_games, media_usb1(folder_games), media_usb1(folder_games_nes), media_usb1(folder_games_md)]
            ),
            "stores": [empty_test_store(), store_smb1_on_usb1(), store_sonic_on_usb1()],
            "ok": [file_nes_smb1, file_md_sonic],
            "errors": [file_a],
            "full_partitions": [MEDIA_FAT],
            "free": {MEDIA_FAT: self.mb600 / 2 - self.size_a, MEDIA_USB1: self.mb600 - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def test_download_three_dbs_with_external_priority_files___with_not_enough_free_space_on_any_partitions___reports_error_for_all_partitions_and_doesnt_save(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(self.mb600, min_space=2000, block_size=32),
            MEDIA_USB1: Partition(self.mb600, min_space=2000, block_size=32)
        })
        self.assertSystem({
            "fs": fs_data(
                files={},
                folders=[folder_games, media_usb1(folder_games)]
            ),
            "stores": [empty_test_store(), empty_test_store(), empty_test_store()],
            "errors": [file_a, file_nes_smb1, file_md_sonic],
            "full_partitions": [MEDIA_FAT, MEDIA_USB1],
            "save": False,
            "free": {MEDIA_FAT: self.mb600 - self.size_a, MEDIA_USB1: self.mb600 - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def test_download_three_dbs_with_external_priority_files___on_second_run_with_not_enough_free_space_on_any_partitions___reports_error_for_all_partitions_and_doesnt_save(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(self.mb600, min_space=2000, block_size=32),
            MEDIA_USB1: Partition(self.mb600, min_space=2000, block_size=32)
        }, input_stores=[
            store_with_folders([folder_a]), store_smb1_on_usb1_but_just_folders(), store_sonic_on_usb1_but_just_folders()
        ], with_fs=fs_external(folders=[folder_a, folder_games, media_usb1(folder_games), media_usb1(folder_games_nes), media_usb1(folder_games_md)]))
        self.assertSystem({
            "fs": fs_data(
                files={},
                folders=[folder_a, folder_games, media_usb1(folder_games), media_usb1(folder_games_nes), media_usb1(folder_games_md)]
            ),
            "stores": [store_with_folders([folder_a]), store_smb1_on_usb1_but_just_folders(), store_sonic_on_usb1_but_just_folders()],
            "errors": [file_a, file_nes_smb1, file_md_sonic],
            "save": False,
            "full_partitions": [MEDIA_FAT, MEDIA_USB1],
            "free": {MEDIA_FAT: self.mb600 - self.size_a, MEDIA_USB1: self.mb600 - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def test_download_three_dbs_with_external_priority_files___with_enough_free_space_on_all_partitions___install_files_on_fat_and_usb1(self):
        sut, free, stores = self.download_three_dbs_with_external_priority_files({
            MEDIA_FAT: Partition(self.mb600, min_space=512, block_size=32),
            MEDIA_USB1: Partition(self.mb600, min_space=512, block_size=32)
        })
        self.assertSystem({
            "fs": fs_data(
                files={**files_a(), **fs_files_smb1_on_usb1(), **fs_files_sonic_on_usb1()},
                folders=[folder_a, folder_games, media_usb1(folder_games), media_usb1(folder_games_nes), media_usb1(folder_games_md)]
            ),
            "stores": [store_test_with_file_a_descr(), store_smb1_on_usb1(), store_sonic_on_usb1()],
            "ok": [file_a, file_nes_smb1, file_md_sonic],
            "free": {MEDIA_FAT: self.mb600 - self.size_a, MEDIA_USB1: self.mb600 - self.size_smb1 - self.size_sonic}
        }, sut, stores, free=free)

    def download_three_dbs_with_external_priority_files(self, partitions: Dict[str, Any], input_stores=None, with_fs=None):
        return self._download_dbs(
            fs_external(folders=[media_usb1(folder_games), media_fat(folder_games)]) if with_fs is None else with_fs,
            [db_test_with_file_a(db_id='1'), db_smb1(db_id='2'), db_sonic(db_id='3')],
            partitions, input_stores=input_stores
        )

    def test_download_db_with_zipped_file___without_enough_space___reports_error_and_full_partition_and_doesnt_save(self):
        sut, free, stores = self.download_db_with_zipped_file({MEDIA_FAT: Partition(1000, min_space=0, block_size=32)})
        self.assertSystem({
            "fs": fs_data(files={}, folders=[]),
            "stores": [empty_test_store()],
            "errors": [cheats_folder_nes_file_path, cheats_folder_sms_file_path],
            "full_partitions": [MEDIA_FAT],
            "save": False,
            "failed_zips": ["test:cheats_id"],
            "free": {MEDIA_FAT: 1000 - self.size_nes_cheat - self.size_sms_cheat}
        }, sut, stores, free=free)

    def test_download_db_with_zipped_file__without_enough_space_with_filled_store___reports_error_and_full_partition_and_doesnt_save(self):
        sut, free, stores = self.download_db_with_zipped_file({MEDIA_FAT: Partition(1000, min_space=0, block_size=32)},
                                                              input_stores=[store_with_unzipped_cheats(url=False)],
                                                              with_fs=fs(folders=cheats_folder_folders()))
        self.assertSystem({
            "fs": fs_data(files={}, folders=cheats_folder_folders()),
            "stores": [store_with_unzipped_cheats(url=False)],
            "errors": [cheats_folder_nes_file_path, cheats_folder_sms_file_path],
            "full_partitions": [MEDIA_FAT],
            "save": False,
            "failed_zips": ["test:cheats_id"],
            "free": {MEDIA_FAT: 1000 - self.size_nes_cheat - self.size_sms_cheat}
        }, sut, stores, free=free)

    def download_db_with_zipped_file(self, partitions: Dict[str, Any], input_stores=None, with_fs=None):
        return self._download_dbs(
            fs() if with_fs is None else with_fs,
            [db_test_descr(zips={
                cheats_folder_id: cheats_folder_zip_desc(
                    zipped_files=zipped_files_from_cheats_folder(),
                    summary=summary_json_from_cheats_folder()
                )
            })],
            partitions, input_stores=input_stores
        )

    def _download_dbs(self, fs_inputs, dbs, partitions, input_stores=None):
        for partition_path, partition in partitions.items():
            if partition.path == '':
                partition.path = partition_path

        free_space_reservation = FakeFreeSpaceReservation(logger=NoLogger(), config=fs_inputs.config, partitions=partitions)
        sut, stores = self._download_databases(fs_inputs, dbs, input_stores=input_stores, free_space_reservation=free_space_reservation)
        return sut, sut.free_space(), stores


class FakeFreeSpaceReservation(LinuxFreeSpaceReservation):
    def _make_partition(self, partition_path: str):
        raise NotImplementedError()


def fs(files=None, folders=None):
    return ImporterImplicitInputs(
        config=config_with(base_path=MEDIA_FAT, base_system_path=MEDIA_FAT, zip_file_count_threshold=0, zip_accumulated_mb_threshold=0),
        files=files,
        folders=folders,
        base_path=MEDIA_FAT
    )


def fs_external(files=None, folders=None):
    return ImporterImplicitInputs(
        config=config_with(storage_priority=STORAGE_PRIORITY_PREFER_EXTERNAL, base_path=MEDIA_FAT, base_system_path=MEDIA_FAT),
        files=files,
        folders=folders,
        base_path=MEDIA_FAT
    )
