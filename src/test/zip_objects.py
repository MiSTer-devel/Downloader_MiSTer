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

from test.objects import zip_desc


def cheats_folder_tag_dictionary():
    return {'nes': 0, 'cheats': 1, 'sms': 2}

cheats_folder_id = 'cheats_id'
cheats_folder_name = 'Cheats'

def cheats_folder_tags():
    return [1]

cheats_folder_nes_folder_name = 'Cheats/NES'
cheats_folder_nes_file_path = cheats_folder_nes_folder_name + '/10-Yard Fight (USA, Europe) [3D564757].zip'
cheats_folder_nes_file_url = f'https://{cheats_folder_nes_folder_name}/10-Yard%20Fight%20%28USA%2C%20Europe%29%20%5B3D564757%5D.zip'
cheats_folder_nes_file_hash = "8c02595fef1096a9dd160e59067f4f4"
cheats_folder_nes_file_size = 1020

def cheats_folder_nes_tags():
    return [0, 1]

cheats_folder_sms_folder_name = 'Cheats/SMS'
cheats_folder_sms_file_path = cheats_folder_sms_folder_name + '/Sonic The Hedgehog (World).zip'
cheats_folder_sms_file_url = f'https://{cheats_folder_sms_folder_name}/Sonic%20The%20Hedgehog%20%28World%29.zip'
cheats_folder_sms_file_hash = "1c111111111096a9dd160e59067f4f4"
cheats_folder_sms_file_size = 2048

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

def cheats_folder_files(zip_id=True, tags=True, url=True):
    return {
        cheats_folder_nes_file_path: cheats_folder_nes_file_descr(zip_id=zip_id, tags=tags, url=url),
        cheats_folder_sms_file_path: cheats_folder_sms_file_descr(zip_id=zip_id, tags=tags, url=url),
    }

def cheats_folder_nes_file_descr(zip_id=True, tags=True, url=True):
    return tweak_descr({
        'hash': cheats_folder_nes_file_hash,
        'size': cheats_folder_nes_file_size,
        'url': cheats_folder_nes_file_url,
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_nes_tags()
    }, zip_id=zip_id, tags=tags, url=url)

def cheats_folder_sms_file_descr(zip_id=True, tags=True, url=True):
    return tweak_descr({
        'hash': cheats_folder_sms_file_hash,
        'size': cheats_folder_sms_file_size,
        'url': cheats_folder_sms_file_url,
        'zip_id': cheats_folder_id,
        'tags': cheats_folder_sms_tags()
    }, zip_id=zip_id, tags=tags, url=url)

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


def store_with_unzipped_cheats(url=True, folders=True, zip_id=True, zips=True, tags=True, online_database_imported=None, summary_hash=None, is_summary_internal=False):
    o = {
        "base_path": "/media/fat/",
        "files": cheats_folder_files(url=url, zip_id=zip_id, tags=tags),
        'folders': cheats_folder_folders(zip_id=zip_id, tags=tags),
        'offline_databases_imported': online_database_imported if online_database_imported is not None else [],
        "zips": {
            cheats_folder_id: cheats_folder_zip_desc(summary_hash=summary_hash, is_summary_internal=is_summary_internal)
        }
    }
    if not folders:
        o.pop('folders')
    if not zips:
        o['zips'] = {}
    if is_summary_internal:
        for zip_description in o['zips'].values():
            zip_description.pop('internal_summary')
    return o

def cheats_folder_zip_desc(zipped_files=None, summary=None, summary_hash=None, is_summary_internal=False):
    json = zip_desc(["NES"], "Cheats/", "Cheats/NES", summary_hash=summary_hash, zipped_files=zipped_files, summary=summary, is_summary_internal=is_summary_internal)
    return json

def summary_json_from_cheats_folder():
    return {
        'files': cheats_folder_files(url=False),
        'folders': cheats_folder_folders(),
    }

def zipped_files_from_cheats_folder():
    return {
        'files': cheats_folder_files(url=False, zip_id=False, tags=False),
        'folders': list(cheats_folder_folders()),
    }

def with_installed_cheats_folder_on_fs(file_system):
    file_system.test_data \
        .with_folders(cheats_folder_folders()) \
        .with_file(cheats_folder_nes_file_path,
                   {"hash": cheats_folder_nes_file_hash, "size": cheats_folder_nes_file_size}) \
        .with_file(cheats_folder_sms_file_path,
                   {"hash": cheats_folder_sms_file_hash, "size": cheats_folder_sms_file_size})

def tweak_descr(o, zip_id=True, tags=True, url=True):
    if not url:
        o.pop('url')
    if not zip_id:
        o.pop('zip_id')
    if not tags:
        o.pop('tags')
    return o
