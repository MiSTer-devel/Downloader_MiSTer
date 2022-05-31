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

from downloader.constants import FILE_PDFViewer, FOLDER_linux, DISTRIBUTION_MISTER_DB_ID
from test.objects import empty_test_store, store_descr, media_fat, file_nes_smb1_descr, file_nes_smb1, folder_games, \
    folder_games_nes, media_usb1, media_usb2, db_entity, remove_all_priority_paths, media_drive, \
    file_pdfviewer_descr, file_nes_contra, file_nes_contra_descr, file_nes_palette_a, file_nes_palette_a_descr, \
    folder_games_nes_palettes, db_test, file_nes_manual, file_nes_manual_descr, folder_docs, folder_docs_nes, db_demo, \
    db_id_external_drives_1, db_id_external_drives_2, file_neogeo_md, file_neogeo_md_descr, file_s32x_md, \
    file_s32x_md_descr, \
    folder_docs_neogeo, folder_docs_s32x, file_foo, file_foo_descr, media_usb0, zip_desc
from test.fake_online_importer import OnlineImporter
from test.zip_objects import zipped_nes_palettes_id, file_nes_palette_a_descr_zipped, zipped_nes_palettes_desc


class OnlineImporterWithPriorityStorageTestBase(unittest.TestCase):

    def download_smb1_db(self, store, inputs):
        return self._download_db(db_with_smb1(), store, inputs)

    def download_empty_db(self, store, inputs):
        return self._download_db(db_entity(), store, inputs)

    def download_smb1_and_contra(self, store, inputs):
        return self._download_db(db_with_smb1_and_contra(), store, inputs)

    def download_smb1_and_palettes(self, store, inputs):
        return self._download_db(db_with_smb1_and_palettes(), store, inputs)

    def download_pdfviewer_db(self, store, inputs):
        return self._download_db(db_with_pdfviewer(), store, inputs)

    def download_zipped_nes_palettes_db(self, store, inputs):
        return self._download_db(db_with_zipped_nes_palettes(), store, inputs)

    def download_smb1_in_db_test_and_nes_manual_in_db_demo(self, inputs):
        local_store_dbs = {
            db_test: empty_test_store(),
            db_demo: empty_test_store(),
        }
        return OnlineImporter\
            .from_implicit_inputs(inputs)\
            .add_db(db_with_smb1(), local_store_dbs[db_test]) \
            .add_db(db_demo_with_nes_manual(), local_store_dbs[db_demo]) \
            .download(False), local_store_dbs

    def download_external_drives_1_and_2(self, inputs):
        local_store_dbs = {
            db_id_external_drives_1: empty_test_store(),
            db_id_external_drives_2: empty_test_store(),
        }
        return OnlineImporter\
            .from_implicit_inputs(inputs)\
            .add_db(db_external_drives_1(), local_store_dbs[db_id_external_drives_1]) \
            .add_db(db_external_drives_2(), local_store_dbs[db_id_external_drives_2]) \
            .download(False), local_store_dbs

    def _download_db(self, db, store, inputs):
        return OnlineImporter\
            .from_implicit_inputs(inputs)\
            .add_db(db, store)\
            .download(False)

    def assertReports(self, sut, installed, save=True):
        self.assertEqual(sorted(remove_all_priority_paths(installed)), sorted(sut.correctly_installed_files()))
        self.assertEqual([], sut.files_that_failed())
        self.assertEqual(False, sut.needs_reboot())
        self.assertEqual(save, sut.needs_save)


delme_drive = '/delme'
hidden_drive = '/hidden'


def fs_files_smb1_on_fat(): return {media_fat(file_nes_smb1): file_nes_smb1_descr()}
def fs_files_smb1_on_usb0(): return {media_usb0(file_nes_smb1): file_nes_smb1_descr()}
def fs_files_smb1_on_usb1(): return {media_usb1(file_nes_smb1): file_nes_smb1_descr()}
def fs_files_smb1_on_usb2(): return {media_usb2(file_nes_smb1): file_nes_smb1_descr()}
def fs_files_smb1_on_delme(): return {media_drive(delme_drive, file_nes_smb1): file_nes_smb1_descr()}
def fs_files_contra_on_fat(): return {media_fat(file_nes_contra): file_nes_contra_descr()}
def fs_files_contra_on_usb0(): return {media_usb0(file_nes_contra): file_nes_contra_descr()}
def fs_files_contra_on_usb1(): return {media_usb1(file_nes_contra): file_nes_contra_descr()}
def fs_files_contra_on_usb2(): return {media_usb2(file_nes_contra): file_nes_contra_descr()}
def fs_files_contra_on_delme(): return {media_drive(delme_drive, file_nes_contra): file_nes_contra_descr()}
def fs_files_smb1_on_fat_and_usb1(): return {**fs_files_smb1_on_fat(), **fs_files_smb1_on_usb1()}
def fs_files_smb1_on_usb1_and_usb2(): return {**fs_files_smb1_on_usb1(), **fs_files_smb1_on_usb2()}
def fs_files_smb1_and_contra_on_fat(): return {**fs_files_smb1_on_fat(), **fs_files_contra_on_fat()}
def fs_files_smb1_and_contra_on_usb0(): return {**fs_files_smb1_on_usb0(), **fs_files_contra_on_usb0()}
def fs_files_smb1_and_contra_on_usb1(): return {**fs_files_smb1_on_usb1(), **fs_files_contra_on_usb1()}
def fs_files_smb1_and_contra_on_usb2(): return {**fs_files_smb1_on_usb2(), **fs_files_contra_on_usb2()}
def fs_files_smb1_and_contra_on_delme(): return {**fs_files_smb1_on_delme(), **fs_files_contra_on_delme()}
def fs_files_smb1_and_contra_on_fat_contra_on_usb1_too(): return {**fs_files_smb1_and_contra_on_fat(), **fs_files_contra_on_usb1()}
def fs_files_smb1_on_fat_contra_on_usb1(): return {**fs_files_smb1_on_fat(), **fs_files_contra_on_usb1()}
def fs_files_smb1_and_contra_on_usb1_smb1_on_fat_too(): return {**fs_files_smb1_on_fat(), **fs_files_smb1_and_contra_on_usb1()}
def fs_files_smb1_and_contra_on_fat_and_usb1(): return {**fs_files_smb1_and_contra_on_fat(), **fs_files_smb1_and_contra_on_usb1()}
def fs_files_pdfviewers_on_hidden(): return {media_drive(hidden_drive, FILE_PDFViewer): file_pdfviewer_descr()}
def fs_files_nes_palettes_on_fat(): return {media_fat(file_nes_palette_a): file_nes_palette_a_descr()}
def fs_files_smb1_and_nes_palettes_on_fat(): return {**fs_files_smb1_on_fat(), **fs_files_nes_palettes_on_fat()}
def fs_files_nes_palettes_on_usb1(): return {media_usb1(file_nes_palette_a): file_nes_palette_a_descr()}
def fs_files_smb1_and_nes_palettes_on_usb1(): return {**fs_files_smb1_on_usb1(), **fs_files_nes_palettes_on_usb1()}
def fs_files_smb1_on_usb1_and_nes_manual_on_usb2(): return {**fs_files_smb1_on_usb1(), media_usb2(file_nes_manual): file_nes_manual_descr()}
def fs_folders_nes_on_fat(): return [media_fat(folder_games), media_fat(folder_games_nes)]
def fs_folders_nes_on_usb1(): return [media_usb1(folder_games), media_usb1(folder_games_nes)]
def fs_folders_nes_on_usb2(): return [media_usb2(folder_games), media_usb2(folder_games_nes)]
def fs_folders_nes_on_delme(): return [media_drive(delme_drive, folder_games), media_drive(delme_drive, folder_games_nes)]
def fs_folders_nes_on_usb1_and_usb2(): return [*fs_folders_nes_on_usb1(), *fs_folders_nes_on_usb2()]
def fs_folders_nes_on_fat_games_on_fat_usb1(): return [*fs_folders_nes_on_fat(), media_usb1(folder_games)]
def fs_folders_nes_on_fat_and_usb1(): return [*fs_folders_nes_on_usb1(), *fs_folders_nes_on_fat()]
def fs_folders_docs_nes_on_usb2(): return [media_usb2(folder_docs), media_usb2(folder_docs_nes)]
def fs_folders_games_nes_on_usb1_and_docs_nes_on_usb2(): return [*fs_folders_nes_on_usb1(), *fs_folders_docs_nes_on_usb2()]
def fs_folders_nes_palettes_on_fat(): return [*fs_folders_nes_on_fat(), media_fat(folder_games_nes_palettes)]
def fs_folders_nes_palettes_on_usb1(): return [*fs_folders_nes_on_usb1(), media_usb1(folder_games_nes_palettes)]
def fs_folders_games_on_usb1_usb2_and_fat(): return [media_fat(folder_games), *fs_folders_games_on_usb1_and_usb2()]
def fs_folders_games_on_usb1_and_usb2(): return [media_usb1(folder_games), media_usb2(folder_games)]
def fs_folders_pdfviewers_on_hidden(): return [media_drive(hidden_drive, FOLDER_linux)]
def store_smb1_on_usb1(): return store_descr(files_usb1=_store_files_smb1(), folders_usb1=_store_folders_nes())
def store_smb1_on_fat_and_usb1(): return store_descr(files=_store_files_smb1(), folders=_store_folders_nes(), files_usb1=_store_files_smb1(), folders_usb1=_store_folders_nes())
def store_smb1_on_delme(): return store_descr(files=_store_files_smb1(), folders=_store_folders_nes(), base_path=delme_drive)
def store_smb1(): return store_descr(files=_store_files_smb1(), folders=_store_folders_nes())
def store_smb1_and_nes_palettes(): return store_descr(files=_store_files_smb1_and_nes_palettes(), folders=_store_folders_nes_palettes())
def store_smb1_and_nes_palettes_on_usb1(): return store_descr(files_usb1=_store_files_smb1_and_nes_palettes(), folders_usb1=_store_folders_nes_palettes())
def store_smb1_on_usb2(): return store_descr(files_usb2=_store_files_smb1(), folders_usb2=_store_folders_nes())
def store_smb1_on_usb1_and_usb2(): return store_descr(files_usb1=_store_files_smb1(), folders_usb1=_store_folders_nes(), files_usb2=_store_files_smb1(), folders_usb2=_store_folders_nes())
def store_games_on_usb1_and_usb2(): return store_descr(folders_usb1=_store_folders_games(), folders_usb2=_store_folders_games())
def store_smb1_and_contra_on_usb1(): return store_descr(files_usb1=_store_files_smb1_and_contra(), folders_usb1=_store_folders_nes())
def store_smb1_and_contra_on_fat_and_usb1(): return store_descr(files=_store_files_smb1_and_contra(), folders=_store_folders_nes(), files_usb1=_store_files_smb1_and_contra(), folders_usb1=_store_folders_nes())
def store_smb1_on_fat_and_smb1_and_contra_on_usb1():return store_descr(files=_store_files_smb1(), folders=_store_folders_nes(), files_usb1=_store_files_smb1_and_contra(), folders_usb1=_store_folders_nes())
def store_smb1_without_folders_on_usb1_and_usb2(): return store_descr(files_usb1=_store_files_smb1(), files_usb2=_store_files_smb1())
def store_smb1_without_folders_on_usb2(): return store_descr(files_usb2=_store_files_smb1())
def store_nes_folder_on_usb1_and_usb2(): return store_descr(folders_usb1=_store_folders_nes(), folders_usb2=_store_folders_nes())
def store_nes_folder_on_usb1(): return store_descr(folders_usb1=_store_folders_nes())
def store_nes_folder_on_usb2(): return store_descr(folders_usb2=_store_folders_nes())
def store_nes_folder(): return store_descr(folders=_store_folders_nes())
def store_smb1_and_games_folder_on_usb1_too(): return store_descr(files=_store_files_smb1(), folders=_store_folders_nes(), folders_usb1=_store_folders_games())
def store_pdfviewer_on_base_system_path_hidden(): return store_descr(files=_store_files_pdfviewer(), folders=_store_folders_linux())
def store_smb1_and_contra(): return store_descr(files=_store_files_smb1_and_contra(), folders=_store_folders_nes())
def store_nes_manual_on_usb2(): return store_descr(files_usb2=_store_files_nes_manual(), folders_usb2=_store_folders_docs_nes())
def store_smb1_on_usb1_and_nes_manual_on_usb2(): return {db_test: store_smb1_on_usb1(), db_demo: store_nes_manual_on_usb2()}
def _store_files_smb1(): return {file_nes_smb1: file_nes_smb1_descr()}
def _store_files_contra(): return {file_nes_contra: file_nes_contra_descr()}
def _store_files_nes_manual(): return {file_nes_manual: file_nes_manual_descr()}
def _store_files_smb1_and_contra(): return {**_store_files_smb1(), **_store_files_contra()}
def _store_files_nes_palettes(): return {file_nes_palette_a: file_nes_palette_a_descr()}
def _store_files_pdfviewer(): return {FILE_PDFViewer: file_pdfviewer_descr()}
def _store_files_foo(): return {file_foo: file_foo_descr()}
def _store_files_s32x_md(): return {file_s32x_md: file_s32x_md_descr()}
def _store_files_neogeo_md(): return {file_neogeo_md: file_neogeo_md_descr()}
def _store_files_foo_smb1_and_s32_md(): return {**_store_files_smb1(), **_store_files_foo(), **_store_files_s32x_md()}
def _store_files_contra_and_neogeo_md(): return {**_store_files_contra(), **_store_files_neogeo_md()}
def _store_folders_games(): return {folder_games: {}}
def _store_folders_docs(): return {folder_docs: {}}
def _store_folders_nes(): return {**_store_folders_games(), folder_games_nes: {}}
def _store_folders_docs_nes(): return {**_store_folders_docs(), folder_docs_nes: {}}
def _store_folders_docs_s32x(): return {**_store_folders_docs(), folder_docs_s32x: {}}
def _store_folders_docs_neogeo(): return {**_store_folders_docs(), folder_docs_neogeo: {}}
def _store_folders_nes_palettes(): return {**_store_folders_nes(), folder_games_nes_palettes: {}}
def _store_folders_linux(): return {FOLDER_linux: {'path': 'system'}}
def _store_files_smb1_and_nes_palettes(): return {**_store_files_nes_palettes(), **_store_files_smb1()}
def db_with_smb1(): return db_entity(files=_store_files_smb1(), folders=_store_folders_nes())
def db_demo_with_nes_manual(): return db_entity(db_id=db_demo, files=_store_files_nes_manual(), folders=_store_folders_docs_nes())
def db_with_smb1_and_contra(): return db_entity(files=_store_files_smb1_and_contra(), folders=_store_folders_nes())
def db_with_smb1_and_palettes(): return db_entity(files=_store_files_smb1_and_nes_palettes(), folders=_store_folders_nes_palettes())
def db_with_pdfviewer(): return db_entity(db_id=DISTRIBUTION_MISTER_DB_ID, files=_store_files_pdfviewer(), folders=_store_folders_linux())
def db_external_drives_1(): return db_entity(db_id=db_id_external_drives_1, files=_store_files_foo_smb1_and_s32_md(), folders=[*_store_folders_nes(), *_store_folders_docs_s32x()])
def db_external_drives_2(): return db_entity(db_id=db_id_external_drives_2, files=_store_files_contra_and_neogeo_md(), folders=[*_store_folders_nes(), *_store_folders_docs_neogeo()])


def db_with_zipped_nes_palettes(): return db_entity(
    folders=_store_folders_nes(),
    zips={zipped_nes_palettes_id: zipped_nes_palettes_desc()}
)


def store_nes_zipped_palettes_on_usb1():
    return store_descr(
        zips=_store_zips_nes_zipped_palettes(),
        files_usb1=_store_files_nes_zipped_palettes(),
        folders_usb1=_store_folders_nes_zipped_palettes()
    )


def store_nes_zipped_palettes_on_fat():
    return store_descr(
        zips=_store_zips_nes_zipped_palettes(),
        files=_store_files_nes_zipped_palettes(),
        folders=_store_folders_nes_zipped_palettes()
    )


def _store_zips_nes_zipped_palettes(): return {zipped_nes_palettes_id: zip_desc("Extracting Palettes", folder_games_nes)}
def _store_files_nes_zipped_palettes(): return {file_nes_palette_a[1:]: {"zip_id": zipped_nes_palettes_id, **file_nes_palette_a_descr_zipped()}}


def _store_folders_nes_zipped_palettes(): return {
        folder_games[1:]: {"zip_id": zipped_nes_palettes_id},
        folder_games_nes[1:]: {"zip_id": zipped_nes_palettes_id},
        folder_games_nes_palettes[1:]: {"zip_id": zipped_nes_palettes_id},
    }
