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
from downloader.other import empty_store


class LocalStoreWrapper:
    def __init__(self, local_store):
        self._local_store = local_store
        self._dirty = False

    def unwrap_local_store(self):
        return self._local_store

    def mark_force_save(self):
        self._dirty = True

    def store_by_id(self, db_id, config):
        if db_id not in self._local_store['dbs']:
            store = empty_store(config[K_BASE_PATH])

            self._local_store['dbs'][db_id] = store
        return StoreWrapper(self._local_store['dbs'][db_id], self)

    def needs_save(self):
        return self._dirty


class StoreWrapper:
    def __init__(self, store, local_store_wrapper):
        if 'external' in store:
            for drive, external in store['external'].items():
                if 'files' in external:
                    store['files'].update(external['files'])
                if 'folders' in external:
                    store['folders'].update(external['folders'])

        self._store = store
        self._local_store_wrapper = local_store_wrapper
        self._read_only = _ReadOnlyStoreAdapter(self._store)
        self._write_only = _WriteOnlyStoreAdapter(self._store, self._local_store_wrapper)

    def unwrap_store(self):
        return self._store

    def write_only(self):
        return self._write_only

    def read_only(self):
        return self._read_only


class _WriteOnlyStoreAdapter:
    def __init__(self, store, top_wrapper):
        self._store = store
        self._top_wrapper = top_wrapper

    def add_file(self, file, description):
        self._add_entry('files', file, description)

    def add_folder(self, folder, description):
        self._add_entry('folders', folder, description)

    def _add_entry(self, kind, path, description):
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
        if 'external' not in self._store or drive not in self._store['external'] or path not in self._store['external'][drive][kind]:
            return

        self._store['external'][drive][kind].pop(path)
        self._top_wrapper.mark_force_save()

    def remove_file(self, file_path):
        self._remove_entry('files', file_path)

    def remove_folder(self, folder_path):
        self._remove_entry('folders', folder_path)

    def _remove_entry(self, kind, path):
        if path not in self._store[kind]:
            return

        self._store[kind].pop(path)
        self._top_wrapper.mark_force_save()

    def add_zip(self, zip_id, description):
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
        if self._store[K_BASE_PATH] == base_path:
            return

        self._store[K_BASE_PATH] = base_path
        self._top_wrapper.mark_force_save()

    def remove_zip_ids(self, removed_zip_ids):
        if not len(removed_zip_ids):
            return

        for zip_id in removed_zip_ids:
            self._store['zips'].pop(zip_id)

        self._remove_non_zip_fields(self._store['files'].values(), removed_zip_ids)
        self._remove_non_zip_fields(self._store['folders'].values(), removed_zip_ids)
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

    def save_filtered_zip_data(self, filtered_zip_data):
        if len(filtered_zip_data):
            if 'filtered_zip_data' in self._store and equal_dicts(self._store['filtered_zip_data'], filtered_zip_data):
                return
            self._store['filtered_zip_data'] = filtered_zip_data

            self._top_wrapper.mark_force_save()
        elif 'filtered_zip_data' in self._store:
            self._store.pop('filtered_zip_data')

            self._top_wrapper.mark_force_save()


class _ReadOnlyStoreAdapter:
    def __init__(self, store):
        self._store = store

    def hash_file(self, file):
        if file not in self._store['files']:
            return 'file_does_not_exist_so_cant_get_hash'

        return self._store['files'][file]['hash']

    def list_missing_files(self, db_files):
        files = {}
        files.update(self._store['files'])
        if 'external' in self._store:
            for external in self._store['external'].values():
                if 'files' in external:
                    files.update(external['files'])
        return {f: d for f, d in files.items() if f not in db_files}

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
    return a == b
