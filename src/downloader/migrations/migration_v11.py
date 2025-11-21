# Copyright (c) 2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from typing import Any

from downloader.store_migrator import MigrationBase


class MigrationV11(MigrationBase):
    version = 11

    def migrate(self, local_store) -> None:
        for db_id, db_description in local_store.get('dbs', {}).items():
            pext_zips = set()
            extract_all_zips = set()
            for zip_id, zip_description in db_description.get('zips', {}).items():
                is_extract_all = False
                if zip_description.get('kind', '') == 'extract_all_contents':
                    is_extract_all = True
                    extract_all_zips.add(zip_id)

                is_pext = False
                if 'target_folder_path' in zip_description and len(zip_description['target_folder_path']) > 0 and zip_description['target_folder_path'][0] == '|':
                    zip_description['target_folder_path'] = zip_description['target_folder_path'][1:]
                    zip_description['path'] = 'pext'
                    is_pext = True
                    pext_zips.add(zip_id)

                if 'internal_summary' in zip_description:
                    internal_summary = zip_description['internal_summary']
                    _migrate_v0(internal_summary)
                    if is_extract_all:
                        if is_pext:
                            _bulk_add_pext(internal_summary)
                        else:
                            _bulk_del_pext(internal_summary)

            _migrate_v0(db_description)
            _fix_pext_according_to_pext_zip(db_description.get('files', {}), pext_zips)
            _fix_pext_according_to_pext_zip(db_description.get('folders', {}), pext_zips)

            for zip_id, data in db_description.get('filtered_zip_data', {}).items():
                _migrate_v0(data)
                if zip_id in extract_all_zips:
                    if zip_id in pext_zips:
                        _bulk_add_pext(data)
                    else:
                        _bulk_del_pext(data)


def _migrate_v0(entries: dict[str, Any]) -> None:
    _bulk_fix_old_pext(entries.get('files', {}))
    _bulk_fix_old_pext(entries.get('folders', {}))

def _bulk_fix_old_pext(entries: dict[str, Any]) -> None:
    old_pext_entries = {f[1:]: _add_pext(d) for f, d in entries.items() if len(f) > 0 and f[0] == '|'}
    if len(old_pext_entries) > 0:
        non_old_pext_entries = {f: d for f, d in entries.items() if len(f) == 0 or f[0] != '|'}
        entries.clear()
        entries.update(non_old_pext_entries)
        entries.update(old_pext_entries)

def _add_pext(desc: dict[str, Any]) -> dict[str, Any]:
    desc['path'] = 'pext'
    return desc

def _del_pext(desc: dict[str, Any]) -> dict[str, Any]:
    if 'path' in desc and desc['path'] == 'pext':
        del desc['path']
    return desc

def _bulk_add_pext(entries: dict[str, Any]) -> None:
    entries['files'] = {f: _add_pext(d) for f, d in entries.get('files', {}).items()}
    entries['folders'] = {f: _add_pext(d) for f, d in entries.get('folders', {}).items()}

def _bulk_del_pext(entries: dict[str, Any]) -> None:
    entries['files'] = {f: _del_pext(d) for f, d in entries.get('files', {}).items()}
    entries['folders'] = {f: _del_pext(d) for f, d in entries.get('folders', {}).items()}

def _fix_pext_according_to_pext_zip(col: dict[str, Any], pext_zips: set[str]) -> None:
    for f, d in col.items():
        if 'zip_id' in d:
            zip_id = d['zip_id']
            if zip_id in pext_zips:
                _add_pext(d)
            else:
                _del_pext(d)
