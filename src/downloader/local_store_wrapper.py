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

from downloader.constants import K_BASE_PATH
from downloader.jobs.index import Index
from downloader.other import empty_store_without_base_path
from typing import Any, Dict, Optional, Set
from collections import defaultdict

NO_HASH_IN_STORE_CODE = 'file_does_not_exist_so_cant_get_hash'


class LocalStoreWrapper:
    def __init__(self, local_store):
        self._local_store = local_store
        self._dirty = False

    def unwrap_local_store(self):
        return self._local_store

    def mark_force_save(self):
        self._dirty = True

    def store_by_id(self, db_id):
        if db_id not in self._local_store['dbs']:
            self._local_store['dbs'][db_id] = empty_store_without_base_path()

        return StoreWrapper(self._local_store['dbs'][db_id], self)

    def needs_save(self):
        return self._dirty


class StoreWrapper:
    def __init__(self, store, local_store_wrapper):
        self._external_additions = {'files': defaultdict(list), 'folders': defaultdict(list)}
        if 'external' in store:
            for drive, external in store['external'].items():
                if 'files' in external:
                    for file_path in external['files']:
                        if file_path in store['files']:
                            continue
                        store['files'][file_path] = external['files'][file_path]
                        self._external_additions['files'][file_path].append(drive)

                if 'folders' in external:
                    for folder_path in external['folders']:
                        if folder_path in store['folders']:
                            continue
                        store['folders'][folder_path] = external['folders'][folder_path]
                        self._external_additions['folders'][folder_path].append(drive)

        self._store = store
        self._local_store_wrapper = local_store_wrapper
        self._read_only = _ReadOnlyStoreAdapter(self._store)
        self._write_only = _WriteOnlyStoreAdapter(self._store, self._local_store_wrapper, self._external_additions)

    def unwrap_store(self):
        return self._store

    def write_only(self):
        return self._write_only

    def read_only(self):
        return self._read_only


class _WriteOnlyStoreAdapter:
    def __init__(self, store, top_wrapper, external_additions):
        self._store = store
        self._top_wrapper = top_wrapper
        self._external_additions = external_additions

    def add_file(self, file, description):
        self._add_entry('files', file, description)

    def add_folder(self, folder, description):
        self._add_entry('folders', folder, description)

    def _add_entry(self, kind, path, description):
        self._clean_external_additions(kind, path)

        if path in self._store[kind] and equal_dicts(self._store[kind][path], description):
            return

        self._store[kind][path] = description
        self._top_wrapper.mark_force_save()

    def add_external_folder(self, drive, folder_path, description):
        self._add_external_entry('folders', drive, folder_path, description)

    def add_external_file(self, drive, file_path, description):
        self._add_external_entry('files', drive, file_path, description)

    def _add_external_entry(self, kind, drive, path, description):
        external = self._external_by_drive(drive)

        entries = external[kind]
        if path in entries and equal_dicts(entries[path], description):
            return

        entries[path] = description
        self._top_wrapper.mark_force_save()

    def _external_by_drive(self, drive):
        if 'external' not in self._store:
            self._store['external'] = {}

        if drive not in self._store['external']:
            self._store['external'][drive] = {'files': {}, 'folders': {}}

        return self._store['external'][drive]

    def remove_external_file(self, drive, file_path):
        self._remove_external_entry('files', drive, file_path)

    def remove_external_folder(self, drive, folder_path):
        self._remove_external_entry('folders', drive, folder_path)

    def _remove_external_entry(self, kind, drive, path):
        self._clean_external_additions(kind, path)

        if 'external' not in self._store or drive not in self._store['external'] or path not in self._store['external'][drive][kind]:
            return

        self._store['external'][drive][kind].pop(path)
        self._top_wrapper.mark_force_save()

    def remove_file(self, file_path):
        self._remove_entry('files', file_path)

    def remove_file_from_zips(self, file_path):
        self._remove_entry_from_zips('files', file_path)

    def remove_folder(self, folder_path):
        self._remove_entry('folders', folder_path)

    def remove_folder_from_zips(self, folder_path):
        self._remove_entry_from_zips('folders', folder_path)

    def _clean_external_additions(self, kind, path):
        if path in self._external_additions[kind]:
            self._external_additions[kind].pop(path)

    def _remove_entry(self, kind, path):
        self._clean_external_additions(kind, path)

        if path not in self._store[kind]:
            return

        self._store[kind].pop(path)
        self._top_wrapper.mark_force_save()

    def _remove_entry_from_zips(self, kind, path):
        if 'zips' not in self._store:
            return

        self._clean_external_additions(kind, path)
        for zip_id, zip_description in self._store['zips'].items():
            if kind in zip_description and path in zip_description[kind]:
                zip_description[kind].pop(path)
                self._top_wrapper.mark_force_save()

    def add_zip(self, zip_id, description, _summary: Dict[str, Any]):
        if 'zipped_files' in description.get('contents_file', {}): del description['contents_file']['zipped_files']
        if 'unzipped_json' in description.get('summary_file', {}): del description['summary_file']['unzipped_json']
        if zip_id in self._store['zips'] and equal_dicts(self._store['zips'][zip_id], description):
            return

        self._store['zips'][zip_id] = description
        self._top_wrapper.mark_force_save()

    def add_imported_offline_database(self, hash_db_file):
        if hash_db_file in self._store['offline_databases_imported']:
            return

        self._store['offline_databases_imported'].append(hash_db_file)
        self._top_wrapper.mark_force_save()

    def set_base_path(self, base_path):
        if K_BASE_PATH in self._store and self._store[K_BASE_PATH] == base_path:
            return

        if K_BASE_PATH in self._store:
            self._top_wrapper.mark_force_save()

        self._store[K_BASE_PATH] = base_path

    def remove_zip_id(self, zip_id):
        self.remove_zip_ids([zip_id])

    def remove_zip_ids(self, removed_zip_ids):
        if not len(removed_zip_ids):
            return

        for zip_id in removed_zip_ids:
            self._store['zips'].pop(zip_id)

        self._remove_non_zip_fields(self._store['files'].values(), removed_zip_ids)
        self._remove_non_zip_fields(self._store['folders'].values(), removed_zip_ids)

        if 'filtered_zip_data' in self._store:
            for zip_id in removed_zip_ids:
                if zip_id in self._store['filtered_zip_data']:
                    self._store['filtered_zip_data'].pop(zip_id)

            if len(self._store['filtered_zip_data']) == 0:
                self._store.pop('filtered_zip_data')

        self._top_wrapper.mark_force_save()

    def try_cleanup_drive(self, drive):
        external = self._external_by_drive(drive)

        if 'files' in external and 'folders' not in external:
            external['folders'] = {}
            self._top_wrapper.mark_force_save()

        elif 'files' not in external and 'folders' in external:
            external['files'] = {}
            self._top_wrapper.mark_force_save()

        if 'files' in external and 'folders' in external and not external['files'] and not external['folders']:
            del external['files']
            del external['folders']
            self._top_wrapper.mark_force_save()

        if not external:
            del self._store['external'][drive]
            self._top_wrapper.mark_force_save()

    def try_cleanup_externals(self):
        for file_path in self._external_additions['files']:
            if file_path in self._store['files']:
                self._store['files'].pop(file_path)
                for drive in self._external_additions['files'][file_path]:
                    if 'external' not in self._store \
                            or drive not in self._store['external'] \
                            or 'files' not in self._store['external'][drive] \
                            or file_path not in self._store['external'][drive]['files']:
                        self._top_wrapper.mark_force_save()

        for folder_path in self._external_additions['folders']:
            if folder_path in self._store['folders']:
                self._store['folders'].pop(folder_path)
                for drive in self._external_additions['files'][folder_path]:
                    if 'external' not in self._store \
                            or drive not in self._store['external'] \
                            or 'folders' not in self._store['external'][drive] \
                            or folder_path not in self._store['external'][drive]['folders']:
                        self._top_wrapper.mark_force_save()

        if not self._store['external']:
            del self._store['external']
            self._top_wrapper.mark_force_save()

    @staticmethod
    def _remove_non_zip_fields(descriptions, removed_zip_ids):
        for description in descriptions:
            if 'zip_id' in description and description['zip_id'] in removed_zip_ids:
                description.pop('zip_id')
                if 'tags' in description:
                    description.pop('tags')

    def populate_with_summary(self, summaries, db_zips):
        for zip_id, summary in summaries:
            self.add_zip(zip_id, db_zips[zip_id], summary)

    def drop_removed_zips_from_store(self, db_zips):
        removed_zip_ids = []
        for zip_id in self._store['zips']:
            if zip_id in db_zips:
                continue

            removed_zip_ids.append(zip_id)

        self.remove_zip_ids(removed_zip_ids)

    def save_filtered_zip_data(self, filtered_zip_data):
        if len(filtered_zip_data):
            if 'filtered_zip_data' in self._store and equal_dicts(self._store['filtered_zip_data'], filtered_zip_data):
                return
            self._store['filtered_zip_data'] = filtered_zip_data

            self._top_wrapper.mark_force_save()
        elif 'filtered_zip_data' in self._store:
            self._store.pop('filtered_zip_data')

            self._top_wrapper.mark_force_save()

    def add_zip_index(self, zip_id: str, index: Index, description: Dict[str, Any]):
        if zip_id in self._store['zips']:
            if not are_zip_descriptions_equal(self._store['zips'][zip_id], description):
                self._store['zips'][zip_id] = description
                self._top_wrapper.mark_force_save()
        else:
            self._store['zips'] = {}

        self._store['zips'][zip_id] = description

        for file_path, file_description in index.files.items():
            self.add_file(file_path, file_description)

        for folder_path, folder_description in index.folders.items():
            self.add_folder(folder_path, folder_description)

        #self._store['zips'][zip_id]['internal_summary'] = {
        #    'files': index.files,
        #    'folders': index.folders,
        #}

    def add_zip_contents(self, zip_id: str, index: Index, description: Dict[str, Any]):
        for file_path, file_description in index.files.items():
            self.add_file(file_path, file_description)

        for folder_path, folder_description in index.folders.items():
            self.add_folder(folder_path, folder_description)


class _ReadOnlyStoreAdapter:
    def __init__(self, store):
        self._store = store

    def hash_file(self, file):
        if file not in self._store['files']:
            return NO_HASH_IN_STORE_CODE

        return self._store['files'][file]['hash']

    def list_missing_files(self, db_files):
        files = {}
        files.update(self._store['files'])
        if 'external' in self._store:
            for external in self._store['external'].values():
                if 'files' in external:
                    files.update(external['files'])
        return {f: d for f, d in files.items() if f not in db_files}

    def zip_index(self, zip_id) -> Optional[Dict[str, Any]]:
        files = {}
        folders = {}
        for file_path, file_description in self._store['files'].items():
            if 'zip_id' in file_description and file_description['zip_id'] == zip_id:
                files[file_path] = file_description

        for folder_path, folder_description in self._store['folders'].items():
            if 'zip_id' in folder_description and folder_description['zip_id'] == zip_id:
                folders[folder_path] = folder_description

        for zip_id, zip_description in self._store.get('filtered_zip_data', {}).items():
            if zip_id != zip_id:
                continue

            for file_path, file_description in zip_description['files'].items():
                if 'zip_id' in file_description and file_description['zip_id'] == zip_id:
                    files[file_path] = file_description

            for folder_path, folder_description in zip_description['folders'].items():
                if 'zip_id' in folder_description and folder_description['zip_id'] == zip_id:
                    folders[folder_path] = folder_description

        if len(files) == 0 and len(folders) == 0:
            return None

        summary_hash = self._store.get('zips', {}).get(zip_id, {}).get('summary_file', {}).get('hash', NO_HASH_IN_STORE_CODE)
        return {'files': files, 'folders': folders, 'hash': summary_hash}

    @property
    def filtered_zip_data(self):
        if 'filtered_zip_data' not in self._store:
            return {}

        return self._store['filtered_zip_data']

    @property
    def zips(self):
        return self._store['zips']

    @property
    def files(self):
        return self._store['files']

    @property
    def folders(self):
        return self._store['folders']

    @property
    def has_externals(self):
        return 'external' in self._store

    @property
    def external_drives(self):
        return list(self._store['external'])

    def external_files(self, drive):
        external = self._store['external'][drive]
        if 'files' in external:
            return external['files']
        else:
            return {}

    def external_folders(self, drive):
        external = self._store['external'][drive]
        if 'folders' in external:
            return external['folders']
        else:
            return []

    @property
    def offline_databases_imported(self):
        return self._store['offline_databases_imported']

    @property
    def externals(self):
        return self._store['external'].items()

    @property
    def base_path(self):
        return self._store[K_BASE_PATH]

    def has_base_path(self):
        return K_BASE_PATH in self._store

    def zip_description(self, zip_id):
        return self._store['zips'][zip_id] if zip_id in self._store['zips'] else {}

    def entries_in_zip(self, entry_kind, zip_ids):
        return {path: fd for path, fd in self._store[entry_kind].items() if 'zip_id' in fd and fd['zip_id'] in zip_ids}

    @property
    def base_path(self):
        return self._store[K_BASE_PATH]

    @property
    def has_no_files(self):
        return len(self._store['files']) == 0


def equal_dicts(a, b):
    if len(a) != len(b):
        return False

    for key, value in a.items():
        if key not in b:
            return False

        if not equal_values(value, b[key]):
            return False

    return True


def equal_lists(a, b):
    if len(a) != len(b):
        return False

    for index, value in enumerate(a):
        if not equal_values(value, b[index]):
            return False

    return True


def equal_values(a, b):
    if isinstance(a, dict) and not equal_dicts(a, b):
        return False

    if isinstance(a, list) and not equal_lists(a, b):
        return False

    return a == b


def zip_description_keys(desc: Dict[str, Any]) -> Set[str]:
    return set(desc.keys()) - {'internal_summary'}


def are_zip_descriptions_equal(desc1: Dict[str, Any], desc2: Dict[str, Any]) -> bool:
    if zip_description_keys(desc1) != zip_description_keys(desc2):
        return False

    file_keys = ['summary_file', 'contents_file']

    if not all(desc1[k] == desc2[k] for k in desc1.keys() if k not in file_keys):
        return False

    for key in file_keys:
        if key in desc1 and not are_zip_file_info_equal(desc1[key], desc2[key]):
            return False

    return True


def are_zip_file_info_equal(file_info1, file_info2):
    return all(file_info1[k] == file_info2[k] for k in ['hash', 'size', 'url'])

