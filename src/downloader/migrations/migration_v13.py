# Copyright (c) 2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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


class MigrationV13(MigrationBase):
    version = 13

    def migrate(self, local_store) -> None:
        dbs = local_store.get('dbs', {})
        if not isinstance(dbs, dict):
            return

        for db in dbs.values():
            if isinstance(db, dict):
                _normalize_fragment(db)


def _normalize_fragment(fragment: dict[str, Any]) -> None:
    target_folder_path = fragment.get('target_folder_path')
    if isinstance(target_folder_path, str) and target_folder_path.startswith('|'):
        fragment['target_folder_path'] = target_folder_path[1:]
        fragment['path'] = 'pext'

    _normalize_entries(fragment.get('files'))
    _normalize_entries(fragment.get('folders'))

    for field in ('zips', 'filtered_zip_data', 'external'):
        children = fragment.get(field, {})
        if not isinstance(children, dict):
            continue
        for child in children.values():
            if isinstance(child, dict):
                _normalize_fragment(child)

    for field in ('internal_summary', 'summary_inline'):
        summary = fragment.get(field)
        if isinstance(summary, dict):
            _normalize_fragment(summary)


def _normalize_entries(entries: Any) -> None:
    if not isinstance(entries, dict):
        return

    old_paths = [path for path in entries if isinstance(path, str) and path.startswith('|')]
    for old_path in old_paths:
        description = entries.pop(old_path)
        path = old_path[1:]
        if path == '' or path in entries:
            continue

        if isinstance(description, dict):
            description['path'] = 'pext'
        entries[path] = description
