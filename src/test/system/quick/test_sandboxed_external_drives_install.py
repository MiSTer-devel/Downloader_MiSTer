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
from pathlib import Path

from test.fake_external_drives_repository import ExternalDrivesRepositoryFactoryStub
from test.objects import path_with
from test.system.quick.sandbox_test_base import local_store_files, hashes, \
    create_folder, load_json, SandboxTestBase, tmp_delme_sandbox, delete_folder, cleanup

tmp_delme_external = '/tmp/delme_external'
tmp_delme_external_drive_0 = path_with(tmp_delme_external, 'drive_0')
tmp_delme_external_drive_1 = path_with(tmp_delme_external, 'drive_1')
tmp_delme_external_drive_2 = path_with(tmp_delme_external, 'drive_2')
tmp_delme_external_drive_3 = path_with(tmp_delme_external, 'drive_3')
tmp_delme_external_priority = (tmp_delme_external_drive_0, tmp_delme_external_drive_1, tmp_delme_external_drive_2, tmp_delme_external_drive_3)

external_downloader_db_json = '.downloader_db.json'
external_downloader_db_json_drive_2 = path_with(tmp_delme_external_drive_2, external_downloader_db_json)
external_downloader_db_json_drive_1 = path_with(tmp_delme_external_drive_1, external_downloader_db_json)
external_downloader_db_json_drive_0 = path_with(tmp_delme_external_drive_0, external_downloader_db_json)

games_folder = 'games/'
games_nes_folder = 'games/NES/'
docs_folder = 'docs/'
docs_s32x_folder = 'docs/S32X/'
docs_neogeo_folder = 'docs/NeoGeo'

smb1_nes_file = 'games/NES/smb1.nes'
contra_nes_file = 'games/NES/contra.nes'
s32x_md_file = 'docs/S32X/S32X.md'
neogeo_md_file = 'docs/NeoGeo/NeoGeo.md'
foo_file = 'foo.txt'

external_smb1_nes_file_drive_2 = path_with(tmp_delme_external_drive_2, smb1_nes_file)
external_contra_nes_file_drive_2 = path_with(tmp_delme_external_drive_2, contra_nes_file)
external_s32x_md_file_drive_1 = path_with(tmp_delme_external_drive_1, s32x_md_file)
external_neogeo_md_file_drive_0 = path_with(tmp_delme_external_drive_0, neogeo_md_file)
external_contra_nes_file_drive_0 = path_with(tmp_delme_external_drive_0, contra_nes_file)
external_smb1_nes_file_drive_0 = path_with(tmp_delme_external_drive_0, smb1_nes_file)
external_s32x_md_file_drive_0 = path_with(tmp_delme_external_drive_0, s32x_md_file)

class TestSandboxedExternalDrivesInstall(SandboxTestBase):
    external_drives_db_1_json = "test/system/fixtures/sandboxed_install/external_drives/external_drives_db_1.json"
    external_drives_db_2_json = "test/system/fixtures/sandboxed_install/external_drives/external_drives_db_2.json"
    external_drives_prefer_sd_ini = "test/system/fixtures/sandboxed_install/external_drives/external_drives_prefer_sd.ini"
    external_drives_prefer_external_ini = "test/system/fixtures/sandboxed_install/external_drives/external_drives_prefer_external.ini"

    def setUp(self) -> None:
        cleanup(self.external_drives_prefer_sd_ini)
        delete_folder(tmp_delme_external)
        delete_folder(tmp_delme_sandbox)
        self._external_drives_repository_factory = ExternalDrivesRepositoryFactoryStub(tmp_delme_external_priority)

    def create_external_drives_folders_with_subfolders(self):
        create_folder(path_with(tmp_delme_external_drive_0, games_folder))
        create_folder(path_with(tmp_delme_external_drive_1, ''))
        create_folder(path_with(tmp_delme_external_drive_2, games_nes_folder))
        create_folder(path_with(tmp_delme_external_drive_3, games_nes_folder))

        create_folder(path_with(tmp_delme_external_drive_0, docs_neogeo_folder))
        create_folder(path_with(tmp_delme_external_drive_1, docs_s32x_folder))
        create_folder(path_with(tmp_delme_external_drive_2, docs_folder))
        create_folder(path_with(tmp_delme_external_drive_3, docs_s32x_folder))

    def test_external_drives_db___with_sd_preference_and_external_subfolders___installs_correctly_on_external_drives(self):
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithNoGamesNoDocs(),
            'files': self.expectedFiles_WithNoGamesNoDocs(),
            'installed_log': [smb1_nes_file, s32x_md_file, foo_file, contra_nes_file, neogeo_md_file]
        })

        self.assertDrives012HaveExpectedFiles()

    def test_external_drives_db___with_sd_preference_and_external_subfolders___reports_none_changes_on_second_time(self):
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({})
        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithNoGamesNoDocs(),
            'files': self.expectedFiles_WithNoGamesNoDocs(),
            'installed_log': ['none.']
        })

        self.assertDrives012HaveExpectedFiles()

    def test_external_drives_db___with_sd_preference_and_external_subfolders___installs_correctly_after_external_drives_with_previous_installation_disappear(self):
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({})

        delete_folder(tmp_delme_external)

        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithGamesAndDocs(),
            'files': self.expectedFiles_WithGamesAndDocs(),
            'installed_log': [s32x_md_file, smb1_nes_file, contra_nes_file, neogeo_md_file]
        })

        self.assertFalse(Path(external_downloader_db_json_drive_0).is_file())
        self.assertFalse(Path(external_downloader_db_json_drive_1).is_file())
        self.assertFalse(Path(external_downloader_db_json_drive_2).is_file())

    def test_external_drives_db___with_sd_preference_and_external_subfolders___installs_correctly_on_external_drives_after_initially_installing_internally(self):

        self.assertExternalDrivesExecutesWithSDPreference({})

        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithGamesAndDocs(),
            'files': self.expectedFiles_WithGamesAndDocs(),
            'installed_log': [s32x_md_file, smb1_nes_file, contra_nes_file, neogeo_md_file]
        })

        self.assertDrives012HaveExpectedFiles()

    def test_external_drives_db___with_sd_preference_and_external_subfolders___installs_correctly_on_external_drives_again_after_removing_and_recreating_them(self):
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({})

        delete_folder(tmp_delme_external)
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithNoGamesNoDocs(),
            'files': self.expectedFiles_WithNoGamesNoDocs(),
            'installed_log': [s32x_md_file, smb1_nes_file, contra_nes_file, neogeo_md_file]
        })

        self.assertDrives012HaveExpectedFiles()

    def create_external_drives_folders_without_subfolders(self):
        create_folder(path_with(tmp_delme_external_drive_0, ''))
        create_folder(path_with(tmp_delme_external_drive_1, ''))
        create_folder(path_with(tmp_delme_external_drive_2, games_folder))
        create_folder(path_with(tmp_delme_external_drive_3, games_folder))

        create_folder(path_with(tmp_delme_external_drive_0, ''))
        create_folder(path_with(tmp_delme_external_drive_1, docs_folder))
        create_folder(path_with(tmp_delme_external_drive_2, docs_folder))
        create_folder(path_with(tmp_delme_external_drive_3, docs_folder))

    def test_external_drives_db___with_sd_preference_but_without_external_subfolders___installs_correctly_on_sd(self):
        self.create_external_drives_folders_without_subfolders()

        self.assertExternalDrivesExecutesWithSDPreference({
            'local_store': self.expectedLocalStore_WithGamesAndDocs(),
            'files': self.expectedFiles_WithGamesAndDocs(),
            'installed_log': [smb1_nes_file, s32x_md_file, foo_file, contra_nes_file, neogeo_md_file]
        })

        self.assertFalse(Path(external_downloader_db_json_drive_0).is_file())
        self.assertFalse(Path(external_downloader_db_json_drive_1).is_file())
        self.assertFalse(Path(external_downloader_db_json_drive_2).is_file())

    def test_external_drives_db___with_external_preference_and_no_subfolders___installs_correctly_on_external_drive_0(self):
        self.create_external_drives_folders_without_subfolders()

        self.assertExternalDrivesExecutesWithExternalPreference({
            'local_store': self.expectedLocalStore_WithNoGamesNoDocs(),
            'files': self.expectedFiles_WithNoGamesNoDocs(),
            'installed_log': [smb1_nes_file, s32x_md_file, foo_file, contra_nes_file, neogeo_md_file]
        })

        self.assertFalse(Path(external_downloader_db_json_drive_1).is_file())
        self.assertFalse(Path(external_downloader_db_json_drive_2).is_file())
        self.assertDrive0HaveAllExpectedFiles()

    def test_external_drives_db___with_external_preference_and_subfolders___installs_correctly_on_different_external_drives(self):
        self.create_external_drives_folders_with_subfolders()

        self.assertExternalDrivesExecutesWithExternalPreference({
            'local_store': self.expectedLocalStore_WithNoGamesNoDocs(),
            'files': self.expectedFiles_WithNoGamesNoDocs(),
            'installed_log': [smb1_nes_file, s32x_md_file, foo_file, contra_nes_file, neogeo_md_file]
        })

        self.assertDrives012HaveExpectedFiles()

    def assertExternalDrivesExecutesWithSDPreference(self, expected):
        self.assertExecutesCorrectly(
            self.external_drives_prefer_sd_ini,
            expected,
            external_drives_repository_factory=self._external_drives_repository_factory
        )

    def assertExternalDrivesExecutesWithExternalPreference(self, expected):
        self.assertExecutesCorrectly(
            self.external_drives_prefer_external_ini,
            expected,
            external_drives_repository_factory=self._external_drives_repository_factory
        )

    def assertDrives012HaveExpectedFiles(self):
        actual_drive_2_db_files, actual_drive_2_ids = self.load_file_list_from_json_db(external_downloader_db_json_drive_2)
        actual_drive_1_db_files, actual_drive_1_ids = self.load_file_list_from_json_db(external_downloader_db_json_drive_1)
        actual_drive_0_db_files, actual_drive_0_ids = self.load_file_list_from_json_db(external_downloader_db_json_drive_0)

        actual_drive_2_fs_files = self.files_from_external_drive(tmp_delme_external_drive_2)
        actual_drive_1_fs_files = self.files_from_external_drive(tmp_delme_external_drive_1)
        actual_drive_0_fs_files = self.files_from_external_drive(tmp_delme_external_drive_0)

        self.assertEqual(['external_drives_1', 'external_drives_2'], actual_drive_2_ids)
        self.assertEqual(['external_drives_1'], actual_drive_1_ids)
        self.assertEqual(['external_drives_2'], actual_drive_0_ids)

        self.assertEqual([external_downloader_db_json_drive_2, external_contra_nes_file_drive_2, external_smb1_nes_file_drive_2], actual_drive_2_fs_files)
        self.assertEqual([external_downloader_db_json_drive_1, external_s32x_md_file_drive_1], actual_drive_1_fs_files)
        self.assertEqual([external_downloader_db_json_drive_0, external_neogeo_md_file_drive_0], actual_drive_0_fs_files)

        self.assertEqual([contra_nes_file, smb1_nes_file], actual_drive_2_db_files)
        self.assertEqual([s32x_md_file], actual_drive_1_db_files)
        self.assertEqual([neogeo_md_file], actual_drive_0_db_files)

    def assertDrive0HaveAllExpectedFiles(self):
        actual_drive_0_db_files, actual_drive_0_ids = self.load_file_list_from_json_db(external_downloader_db_json_drive_0)
        actual_drive_0_fs_files = set(self.files_from_external_drive(tmp_delme_external_drive_0))

        self.assertEqual(['external_drives_1', 'external_drives_2'], actual_drive_0_ids)
        self.assertEqual({external_downloader_db_json_drive_0, external_contra_nes_file_drive_0, external_smb1_nes_file_drive_0, external_s32x_md_file_drive_0, external_neogeo_md_file_drive_0}, actual_drive_0_fs_files)
        self.assertEqual({contra_nes_file, smb1_nes_file, s32x_md_file, neogeo_md_file}, set(actual_drive_0_db_files))

    def expectedLocalStore_WithNoGamesNoDocs(self):
        return local_store_files([
            ('external_drives_1', self.expectedInternalDb1Files_WithNoGamesNoDocs()),
            ('external_drives_2', self.expectedInternalDb2Files_WithNoGamesNoDocs()),
        ])

    def expectedFiles_WithNoGamesNoDocs(self):
        return hashes(tmp_delme_sandbox, self.expectedInternalDb1Files_WithNoGamesNoDocs())

    def expectedInternalDb1Files_WithNoGamesNoDocs(self):
        input_db = load_json(self.external_drives_db_1_json)
        return {f: d for f, d in input_db['files'].items() if f[0] != '|'}

    def expectedInternalDb2Files_WithNoGamesNoDocs(self):
        input_db = load_json(self.external_drives_db_2_json)
        return {f: d for f, d in input_db['files'].items() if f[0] != '|'}

    def expectedLocalStore_WithGamesAndDocs(self):
        db_1 = load_json(self.external_drives_db_1_json)
        db_2 = load_json(self.external_drives_db_2_json)
        return local_store_files([
            ('external_drives_1', db_1['files'], db_1['folders']),
            ('external_drives_2', db_2['files'], db_2['folders']),
        ])

    def expectedFiles_WithGamesAndDocs(self):
        db_1 = load_json(self.external_drives_db_1_json)
        db_2 = load_json(self.external_drives_db_2_json)
        return sorted([*hashes(tmp_delme_sandbox, db_1['files']), *hashes(tmp_delme_sandbox, db_2['files'])])

    def files_from_external_drive(self, drive_path):
        return [file[0] for file in self.find_all_files(path_with(drive_path, ''))]

    def load_file_list_from_json_db(self, path):
        db = load_json(path)
        self.assertIn('migration_version', db)
        self.assertGreater(db['migration_version'], 0)

        files = {}
        db_ids = set()
        for db_id, db_content in db['dbs'].items():
            files.update(db_content['files'])
            db_ids.add(db_id)

        return sorted(list(files)), sorted(list(db_ids))

