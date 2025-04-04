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

from downloader.constants import K_BASE_PATH
from test.objects_old_pext import zip_desc, file_nes_palette_a, tweak_descr, folder_games_nes, folder_games, \
    folder_games_nes_palettes, file_nes_palette_a_descr, zipped_nes_palettes_id

# @TODO: Remove this file when support for the old pext syntax '|' is removed

def cheats_folder_tag_dictionary():
    return {'nes': 0, 'cheats': 1, 'sms': 2}


cheats_folder_id = 'cheats_id'
cheats_folder_name = 'Cheats'


def zipped_nes_palettes_desc(summary_internal_zip_id=None, url: bool = True, tags: bool = False, zipped_files: bool = True, summary: bool = True):
    return zip_desc(
        "Extracting Palettes",
        folder_games_nes + '/',
        summary={
            "files": {file_nes_palette_a: file_nes_palette_a_descr_zipped(url=url, tags=tags)},
            "folders": {
                folder_games: tweak_descr({"zip_id": zipped_nes_palettes_id, "tags": ["games"]}, tags=tags),
                folder_games_nes: tweak_descr({"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes"]}, tags=tags),
                folder_games_nes_palettes: tweak_descr({"zip_id": zipped_nes_palettes_id, "tags": ["games", "nes", "palette"]}, tags=tags),
            }
        } if summary else None,
        zipped_files={
            "files": {file_nes_palette_a.removeprefix(folder_games_nes + '/'): file_nes_palette_a_descr()},
            "folders": {}
        } if zipped_files else None,
        summary_internal_zip_id=summary_internal_zip_id
    )


def cheats_folder_tags():
    return [1]


cheats_folder_nes_folder_name = 'Cheats/NES'
cheats_folder_nes_file_zip_path = 'NES/10-Yard Fight (USA, Europe) [3D564757].zip'
cheats_folder_nes_file_path = 'Cheats/' + cheats_folder_nes_file_zip_path
cheats_folder_nes_file_url = f'https://{cheats_folder_nes_folder_name}/10-Yard%20Fight%20%28USA%2C%20Europe%29%20%5B3D564757%5D.zip'
cheats_folder_nes_file_hash = "8c02595fef1096a9dd160e59067f4f4"
cheats_folder_nes_file_size = 1020


def cheats_folder_nes_file_description():
    return {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size}


def cheats_folder_nes_tags():
    return [0, 1]


cheats_folder_sms_folder_name = 'Cheats/SMS'
cheats_folder_sms_file_zip_path = 'SMS/Sonic The Hedgehog (World).zip'
cheats_folder_sms_file_path = 'Cheats/' + cheats_folder_sms_file_zip_path
cheats_folder_sms_file_url = f'https://{cheats_folder_sms_folder_name}/Sonic%20The%20Hedgehog%20%28World%29.zip'
cheats_folder_sms_file_hash = "1c111111111096a9dd160e59067f4f4"
cheats_folder_sms_file_size = 2048


def cheats_folder_sms_file_description():
    return {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size}


def cheats_folder_sms_tags():
    return [2, 1]


def cheats_folder_folders(zip_id=True, tags=True):
    return {
        cheats_folder_nes_folder_name: cheats_folder_nes_folder_descr(zip_id=zip_id, tags=tags),
        cheats_folder_sms_folder_name: cheats_folder_sms_folder_descr(zip_id=zip_id, tags=tags),
        cheats_folder_name: cheats_folder_descr(zip_id=zip_id, tags=tags)
    }


def cheats_folder_only_nes_folders(zip_id=True, tags=True):
    return {
        cheats_folder_nes_folder_name: cheats_folder_nes_folder_descr(zip_id=zip_id, tags=tags),
        cheats_folder_name: cheats_folder_descr(zip_id=zip_id, tags=tags)
    }


def cheats_folder_files(zip_id=True, tags=True, url=True, is_internal_summary=False, zip_path=False):
    return {
        cheats_folder_nes_file_zip_path if zip_path else cheats_folder_nes_file_path: cheats_folder_nes_file_descr(zip_id=zip_id, tags=tags, url=url, zip_path=is_internal_summary),
        cheats_folder_sms_file_zip_path if zip_path else cheats_folder_sms_file_path: cheats_folder_sms_file_descr(zip_id=zip_id, tags=tags, url=url, zip_path=is_internal_summary),
    }


def cheats_folder_nes_file_descr(zip_id=True, tags=True, url=True, zip_path=False):
    return tweak_descr({
        'hash': cheats_folder_nes_file_hash,
        'size': cheats_folder_nes_file_size,
        'url': cheats_folder_nes_file_url,
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_nes_tags()
    }, zip_id=zip_id, tags=tags, url=url, zip_path=zip_path)


def cheats_folder_sms_file_descr(zip_id=True, tags=True, url=True, zip_path=False):
    return tweak_descr({
        'hash': cheats_folder_sms_file_hash,
        'size': cheats_folder_sms_file_size,
        'url': cheats_folder_sms_file_url,
        'zip_id': cheats_folder_id,
        'zip_path': cheats_folder_sms_file_zip_path,
        'tags': cheats_folder_sms_tags()
    }, zip_id=zip_id, tags=tags, url=url, zip_path=zip_path is not None)


def cheats_folder_nes_folder_descr(zip_id=True, tags=True):
    return tweak_descr({
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_nes_tags()
    }, zip_id=zip_id, tags=tags)


def cheats_folder_sms_folder_descr(zip_id=True, tags=True):
    return tweak_descr({
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_sms_tags()
    }, zip_id=zip_id, tags=tags)


def cheats_folder_descr(zip_id=True, tags=True):
    return tweak_descr({
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_tags()
    }, zip_id=zip_id, tags=tags)

def folders_games_nes_palettes(zip_id=True):
    return {
        folder_games: tweak_descr({'zip_id': zipped_nes_palettes_id}, zip_id=zip_id),
        folder_games_nes: tweak_descr({'zip_id': zipped_nes_palettes_id}, zip_id=zip_id),
        folder_games_nes_palettes: tweak_descr({'zip_id': zipped_nes_palettes_id}, zip_id=zip_id),
    }


def store_with_unzipped_cheats(url=False, folders=True, files=True, zip_id=True, zips=True, tags=True, summary_hash=None, is_internal_summary=False):
    summary_internal_zip_id = cheats_folder_id if is_internal_summary else None
    o = {
        K_BASE_PATH: "/media/fat",
        "files": {k: v for k, v in cheats_folder_files(url=url, zip_id=zip_id, tags=tags, is_internal_summary=is_internal_summary).items()},
        'folders': {k: v for k, v in cheats_folder_folders(zip_id=zip_id, tags=tags).items()},
        "zips": {
            cheats_folder_id: cheats_folder_zip_desc(summary_hash=summary_hash, summary_internal_zip_id=summary_internal_zip_id)
        }
    }
    if not folders:
        o['folders'] = {}
    if not files:
        o['files'] = {}
    if not zips:
        o['zips'] = {}
    if is_internal_summary:
        for zip_description in o['zips'].values():
            zip_description.pop('internal_summary')
    return o


def cheats_folder_zip_desc(zipped_files=None, summary=None, summary_hash=None, summary_internal_zip_id=None):
    json = zip_desc("Extracting NES Cheats folder", "Cheats/", summary_hash=summary_hash, zipped_files=zipped_files, summary=summary, summary_internal_zip_id=summary_internal_zip_id)
    return json


def summary_json_from_cheats_folder():
    return {
        'files': cheats_folder_files(url=False),
        'folders': cheats_folder_folders(),
    }


def zipped_files_from_cheats_folder():
    return {
        'files': cheats_folder_files(url=False, zip_id=False, tags=False, zip_path=True),
        'folders': cheats_folder_folders(),
    }


def file_nes_palette_a_descr_zipped(zip_id=True, url=True, tags=False):
    return file_nes_palette_a_descr(zip_id=zip_id, url=url, tags=tags)


def files_nes_palettes(zip_id=True, url=True):
    return {
        file_nes_palette_a: file_nes_palette_a_descr_zipped(zip_id=zip_id, url=url)
    }


def with_installed_cheats_folder_on_fs(file_system_state):
    file_system_state \
        .add_folders(cheats_folder_folders())\
        .add_file(base_path=None, file=cheats_folder_nes_file_path,
                   description={"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size}) \
        .add_file(base_path=None, file=cheats_folder_sms_file_path,
                   description={"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size})


def with_installed_nes_palettes_on_fs(file_system_state):
    file_system_state \
        .add_folders(folders_games_nes_palettes())\
        .add_file(base_path=None, file=file_nes_palette_a[1:],
                   description=file_nes_palette_a_descr(url=False))
