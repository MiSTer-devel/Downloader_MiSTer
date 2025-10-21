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
            if 'internal_summary' in db_description:
                internal_summary = db_description['internal_summary']
                _migrate_v0(internal_summary.get('files', {}), internal_summary.get('folders', {}))
            if 'filtered_zip_data' in db_description:
                for zip_id, data in db_description['filtered_zip_data'].items():
                    _migrate_v0(data.get('files', {}), data.get('folders', {}))

def _migrate_v0(files: dict[str, Any], folders: dict[str, Any]) -> None:
    _fix_old_pext(files)
    _fix_old_pext(folders)


def _fix_old_pext(entries: dict[str, Any]) -> None:
    old_pext_entries = {f[1:]: _add_pext(d) for f, d in entries.items() if f[0] == '|'}
    if len(old_pext_entries) > 0:
        non_old_pext_entries = {f: d for f, d in entries.items() if f[0] != '|'}
        entries.clear()
        entries.update(non_old_pext_entries)
        entries.update(old_pext_entries)

def _add_pext(desc: dict[str, Any]) -> dict[str, Any]:
    desc['path'] = 'pext'
    return desc
