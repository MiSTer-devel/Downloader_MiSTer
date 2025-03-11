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

from downloader.constants import K_BASE_PATH, DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE, \
    DB_STATE_SIGNATURE_NO_TIMESTAMP, DB_STATE_SIGNATURE_NO_FILTER
from downloader.jobs.index import Index
from downloader.other import empty_store_without_base_path
from typing import Any, Dict, Optional, Set, Tuple, List, TypedDict
from collections import defaultdict, ChainMap

from downloader.path_package import PathPackage, PathType

NO_HASH_IN_STORE_CODE = 'file_does_not_exist_so_cant_get_hash'


class StoreFragmentPaths(TypedDict):
    files: Dict[str, Any]
    folders: Dict[str, Any]

class StoreFragmentZipSummary(StoreFragmentPaths, total=False):
    hash: str

def new_store_fragment_paths() -> StoreFragmentPaths: return {"files": dict(), "folders": dict()}


class StoreFragmentDrivePaths(TypedDict):
    base_paths: StoreFragmentPaths
    external_paths: Dict[str, StoreFragmentPaths]

def new_store_fragment_drive_paths(): return {"base_paths": new_store_fragment_paths(), "external_paths": dict()}

class DbStateSig(TypedDict):
    hash: str
    size: int
    timestamp: int
    filter: str

def empty_db_state_signature() -> DbStateSig: return {'hash': DB_STATE_SIGNATURE_NO_HASH, 'size': DB_STATE_SIGNATURE_NO_SIZE, 'timestamp': DB_STATE_SIGNATURE_NO_TIMESTAMP, 'filter': DB_STATE_SIGNATURE_NO_FILTER}

class LocalStore(TypedDict):
    dbs: dict[str, Any]
    db_sigs: dict[str, Any]

class LocalStoreWrapper:
    def __init__(self, local_store: LocalStore):
        self._local_store = local_store
        self._dirty = False

    def unwrap_local_store(self) -> LocalStore:
        return self._local_store

    def mark_force_save(self) -> None:
        self._dirty = True

    def store_by_id(self, db_id: str) -> 'StoreWrapper':
        if db_id not in self._local_store['dbs'] or self._local_store['dbs'] is None:
            self._local_store['dbs'][db_id] = empty_store_without_base_path()

        if db_id not in self._local_store['db_sigs'] or self._local_store['db_sigs'] is None:
            self._local_store['db_sigs'][db_id] = empty_db_state_signature()

        return StoreWrapper(self._local_store['dbs'][db_id], self._local_store['db_sigs'][db_id], self)

    def needs_save(self) -> bool:
        return self._dirty


class ReadOnlyStoreException(Exception): pass


class StoreWrapper:
    def __init__(self, store: Dict[str, Any], db_state_signature: DbStateSig, local_store_wrapper: LocalStoreWrapper, readonly: bool = False):
        self._external_additions: StoreFragmentPaths = {'files': defaultdict(list), 'folders': defaultdict(list)}
        if 'external' in store:
            for drive, external in store['external'].items():
                if 'files' in external:
                    for file_path in external['files']:
                        if file_path in store['files']:
                            continue
                        #store['files'][file_path] = external['files'][file_path]
                        self._external_additions['files'][file_path].append(drive)

                if 'folders' in external:
                    for folder_path in external['folders']:
                        if folder_path in store['folders']:
                            continue
                        #store['folders'][folder_path] = external['folders'][folder_path]
                        self._external_additions['folders'][folder_path].append(drive)

        self._store = store
        self._db_state_signature = db_state_signature
        self._local_store_wrapper = local_store_wrapper
        self._read_only = ReadOnlyStoreAdapter(self._store, self._db_state_signature)
        self._write_only = WriteOnlyStoreAdapter(self._store, self._db_state_signature, self._local_store_wrapper, self._external_additions)
        self._readonly = readonly

    def unwrap_store(self) -> Dict[str, Any]:
        return self._store

    def write_only(self) -> 'WriteOnlyStoreAdapter':
        if self._readonly: raise ReadOnlyStoreException('Cannot get write only store adapter from read only store wrapper')
        return self._write_only

    def read_only(self) -> 'ReadOnlyStoreAdapter':
        return self._read_only
    
    def select(self, index: Index) -> 'StoreWrapper':
        # @TODO: Remove this | handling after we change the pext path format in the stores
        norm_files = [fp[1:] if len(fp) > 0 and fp[0] == '|' else fp for fp in index.files]
        norm_folders = [dp[1:] if len(dp) > 0 and dp[0] == '|' else dp for dp in index.folders]

        new_store = {
            'files': {fp: self._store['files'][fp] for fp in norm_files if fp in self._store['files']},
            'folders': {fp: self._store['folders'][fp] for fp in norm_folders if fp in self._store['folders']},
        }

        if 'base_path' in self._store:
            new_store['base_path'] = self._store['base_path']

        if 'external' in self._store:
            new_store['external'] = {
                drive: {
                    'files': {fp: summary['files'][fp] for fp in norm_files if fp in summary['files']},
                    'folders': {dp: summary['folders'][dp] for dp in norm_folders if dp in summary['folders']}
                }
                for drive, summary in self._store['external'].items()
            }

        return StoreWrapper(new_store, empty_db_state_signature(), self._local_store_wrapper, readonly=True)

    def deselect_all(self, indexes: List[Index]) -> 'StoreWrapper':
        # @TODO: Remove this | handling after we change the pext path format in the stores
        norm_files = {fp if (fp[0] != '|' or len(fp) == 0) else fp[1:] for index in indexes for fp in index.files}
        norm_folders = {dp if (dp[0] != '|' or len(dp) == 0) else dp[1:] for index in indexes for dp in index.folders}

        new_store = {
            'files': {fp: fd for fp, fd in self._store['files'].items() if fp not in norm_files},
            'folders': {dp: dd for dp, dd in self._store['folders'].items() if dp not in norm_folders},
        }

        if 'base_path' in self._store:
            new_store['base_path'] = self._store['base_path']

        if 'external' in self._store:
            new_store['external'] = {
                drive: {
                    'files': {fp: fd for fp, fd in summary['files'].items() if fp not in norm_files},
                    'folders': {dp: dd for dp, dd in summary['folders'].items() if dp not in norm_folders}
                }
                for drive, summary in self._store['external'].items()
            }

        return StoreWrapper(new_store, empty_db_state_signature(), self._local_store_wrapper, readonly=True)


class WriteOnlyStoreAdapter:
    def __init__(self, store, db_state_signature, top_wrapper, external_additions):
        self._store = store
        self._db_state_signature = db_state_signature
        self._top_wrapper = top_wrapper
        self._external_additions = external_additions

    def add_file_pkg(self, file_pkg: PathPackage, has_repeated_presence: bool = False):
        if file_pkg.pext_props is not None and file_pkg.is_pext_external():
            self.add_external_file(file_pkg.pext_props.drive, file_pkg.rel_path, file_pkg.description, has_repeated_presence)
        else:
            self.add_file(file_pkg.rel_path, file_pkg.description)

    def remove_file_pkg(self, file_pkg: PathPackage):
        if file_pkg.is_pext_external():
            self.remove_external_file(file_pkg.drive, file_pkg.rel_path)
        else:
            self.remove_local_file(file_pkg.rel_path)

    def add_folder_pkg(self, folder_pkg: PathPackage):
        if folder_pkg.pext_props is not None and folder_pkg.is_pext_external():
            self.add_external_folder(folder_pkg.pext_props.drive, folder_pkg.rel_path, folder_pkg.description)
        else:
            self.add_folder(folder_pkg.rel_path, folder_pkg.description)

    def remove_folder_pkg(self, folder_pkg: PathPackage):
        if folder_pkg.is_pext_external():
            self.remove_external_folder(folder_pkg.drive, folder_pkg.rel_path)
        else:
            self.remove_local_folder(folder_pkg.rel_path)

    def add_file(self, file_path, description):
        if file_path in self._external_additions['files']:
            for drive in self._external_additions['files'][file_path]:
                self.remove_external_file(drive, file_path)
        self._add_entry('files', PathType.FILE, file_path, description)

    def add_folder(self, folder, description):
        self._add_entry('folders', PathType.FOLDER, folder, description)

    def _add_entry(self, kind: str, ty: PathType, path: str, description: dict[str, Any]):
        self._clean_external_additions(kind, path)

        if 'zip_id' not in description and 'tags' in description:
            description.pop('tags')

        if path in self._store[kind] and equal_descriptions(self._store[kind][path], description, ty):
            return

        self._store[kind][path] = description
        self._top_wrapper.mark_force_save()

    def add_external_folder(self, drive, folder_path, description):
        self._add_external_entry('folders', PathType.FOLDER, drive, folder_path, description)

    def add_external_file(self, drive: str, file_path: str, description: dict[str, Any], has_repeated_presence: bool = False):
        if file_path in self._store['files'] and not has_repeated_presence:
            self.remove_file(file_path)
        if file_path in self._external_additions['files'] and not has_repeated_presence:
            for d in self._external_additions['files'][file_path]:
                if d == drive:
                    continue
                self.remove_external_file(d, file_path)
        self._add_external_entry('files', PathType.FILE, drive, file_path, description)

    def _add_external_entry(self, kind: str, ty: PathType, drive: str, path: str, description: dict[str, Any]):
        external = self._external_by_drive(drive)

        if 'zip_id' not in description and 'tags' in description:
            description.pop('tags')

        entries = external[kind]
        if path in entries and equal_descriptions(entries[path], description, ty):
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

    def remove_local_file(self, file_path):
        self._remove_local_entry('files', file_path)

    def remove_local_folder(self, folder_path):
        self._remove_local_entry('folders', folder_path)

    def remove_external_folder(self, drive, folder_path):
        self._remove_external_entry('folders', drive, folder_path)

    def _remove_external_entry(self, kind, drive, path):
        if 'external' not in self._store or drive not in self._store['external'] or path not in self._store['external'][drive][kind]:
            return

        self._store['external'][drive][kind].pop(path)
        self._top_wrapper.mark_force_save()

    def remove_file(self, file_path: str):
        self._remove_entry('files', file_path)

    def remove_file_from_zips(self, file_path: str):
        self._remove_entry_from_zips('files', file_path)

    def remove_local_folder_from_zips(self, folder_path: str):
        self._remove_local_entry_from_zips('folders', folder_path)

    def remove_external_folder_from_zips(self, drive: str, folder_path: str):
        self._remove_external_entry_from_zips('folders', drive, folder_path)

    def _clean_external_additions(self, kind, path):
        if path in self._external_additions[kind]:
            self._external_additions[kind].pop(path)

        if 'external' not in self._store:
            return

        changed = False
        for drive, summary in self._store['external'].items():
            if path in summary[kind]:
                summary[kind].pop(path)
                changed = True

        if changed: self._top_wrapper.mark_force_save()

    def _remove_entry(self, kind, path):
        #self._clean_external_additions(kind, path)
        self._remove_local_entry(kind, path)

    def _remove_local_entry(self, kind, path):
        if path not in self._store[kind]:
            return

        self._store[kind].pop(path)
        self._top_wrapper.mark_force_save()

    def _remove_entry_from_zips(self, kind: str, path: str):
        if 'zips' not in self._store:
            return

        self._clean_external_additions(kind, path)
        for zip_id, zip_description in self._store['zips'].items():
            if kind in zip_description and path in zip_description[kind]:
                zip_description[kind].pop(path)
                self._top_wrapper.mark_force_save()

    def _remove_local_entry_from_zips(self, kind: str, path: str):
        if 'zips' not in self._store:
            return

        for zip_id, zip_description in self._store['zips'].items():
            if kind in zip_description and path in zip_description[kind]:
                zip_description[kind].pop(path)
                self._top_wrapper.mark_force_save()

    def _remove_external_entry_from_zips(self, kind: str, drive: str, path: str):
        if 'zips' not in self._store:
            return

        if path in self._external_additions[kind]:
            self._external_additions[kind].pop(path)

        if 'external' in self._store and drive in self._store['external']:
            external = self._store['external'][drive][kind]
            if path in external:
                external.pop(path)
                self._top_wrapper.mark_force_save()

        for zip_id, zip_description in self._store['zips'].items():
            if kind in zip_description and path in zip_description[kind]:
                zip_description[kind].pop(path)
                self._top_wrapper.mark_force_save()

    def set_base_path(self, base_path):
        if K_BASE_PATH in self._store and self._store[K_BASE_PATH] == base_path:
            return

        if K_BASE_PATH in self._store:
            self._top_wrapper.mark_force_save()

        self._store[K_BASE_PATH] = base_path

    def set_db_state_signature(self, transfer_hash: str, transfer_size: int, timestamp: int, filter: str):
        if self._db_state_signature['hash'] != transfer_hash:
            self._db_state_signature['hash'] = transfer_hash
            self._top_wrapper.mark_force_save()

        if self._db_state_signature['size'] != transfer_size:
            self._db_state_signature['size'] = transfer_size
            self._top_wrapper.mark_force_save()

        if self._db_state_signature['timestamp'] != timestamp:
            self._db_state_signature['timestamp'] = timestamp
            self._top_wrapper.mark_force_save()

        if self._db_state_signature['filter'] != filter:
            self._db_state_signature['filter'] = filter
            self._top_wrapper.mark_force_save()


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

    def cleanup_externals(self):
        if 'external' in self._store:
            for drive in list(self._store['external']):
                self.try_cleanup_drive(drive)

            self.try_cleanup_externals()

    def try_cleanup_drive(self, drive):
        external = self._external_by_drive(drive)

        if 'files' in external and 'folders' not in external:
            external['folders'] = {}
            self._top_wrapper.mark_force_save()

        elif 'files' not in external and 'folders' in external:
            external['files'] = {}
            self._top_wrapper.mark_force_save()

        if 'files' in external and not external['files'] and 'folders' in external and not external['folders']:
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

    def save_filtered_zip_data(self, filtered_zip_data):
        for zip_id in list(filtered_zip_data):
            data = filtered_zip_data[zip_id]
            empty_files = 'files' not in data or len(data['files']) == 0
            empty_folders = 'folders' not in data or len(data['folders']) == 0
            if empty_files and empty_folders:
                filtered_zip_data.pop(zip_id)

        if len(filtered_zip_data):
            if 'filtered_zip_data' in self._store and equal_dicts(self._store['filtered_zip_data'], filtered_zip_data):
                return
            self._store['filtered_zip_data'] = filtered_zip_data

            self._top_wrapper.mark_force_save()
        elif 'filtered_zip_data' in self._store:
            self._store.pop('filtered_zip_data')

            self._top_wrapper.mark_force_save()

    def add_zip_summary(self, zip_id: str, fragment: StoreFragmentDrivePaths, description: Dict[str, Any]):
        if zip_id in self._store['zips']:
            if not are_zip_descriptions_equal(self._store['zips'][zip_id], description):
                self._store['zips'][zip_id] = description
                self._top_wrapper.mark_force_save()
        else:
            self._store['zips'][zip_id] = description
            self._top_wrapper.mark_force_save()

        for file_path, file_description in fragment['base_paths']['files'].items():
            self.add_file(file_path, file_description)

        for folder_path, folder_description in fragment['base_paths']['folders'].items():
            self.add_folder(folder_path, folder_description)

        for drive, paths in fragment['external_paths'].items():
            for file_path, file_description in paths['files'].items():
                self.add_external_file(drive, file_path, file_description)

            for folder_path, folder_description in paths['folders'].items():
                self.add_external_folder(drive, folder_path, folder_description)

class ReadOnlyStoreAdapter:
    def __init__(self, store, db_state_signature):
        self._store = store
        self._db_state_signature = db_state_signature

    def invalid_hashes(self, file_pkgs: List[PathPackage]) -> List[bool]:
        '''Returns a list of booleans indicating invalid hashes with the same order as the input.'''
        store_files = self._store['files']
        return [
            (store_files[pkg.rel_path]['hash'] != pkg.description['hash'] if pkg.rel_path in store_files else True) 
            if not pkg.is_pext_external() else
            (True if 'external' not in self._store \
                else True if pkg.drive not in self._store['external'] \
                    else True if pkg.rel_path not in self._store['external'][pkg.drive]['files'] \
                        else self._store['external'][pkg.drive]['files'][pkg.rel_path]['hash'] != pkg.description['hash'])
            for pkg in file_pkgs
        ]

    def zip_summaries(self) -> dict[str, Any]:
        grouped: dict[str, StoreFragmentZipSummary] = defaultdict(lambda: {'files': {}, 'folders': {}})

        # @TODO: This if startswith('games') should be removed when we store all the zip information on the store
        #        Explicit asking for games is a hack, as this should only be declared in the database information. Remove ASAP

        for fp, fd in self._store.get('files', {}).items():
            if 'zip_id' not in fd: continue
            grouped[fd['zip_id']]['files'][fp] = fd

        for dp, dd in self._store.get('folders', {}).items():
            if 'zip_id' not in dd: continue
            grouped[dd['zip_id']]['folders'][dp] = dd

        for summary in self._store.get('external', {}).values():
            for fp, fd in summary.get('files', {}).items():
                if 'zip_id' not in fd: continue
                grouped[fd['zip_id']]['files'][fp] = fd

        for summary in self._store.get('external', {}).values():
            for dp, dd in summary.get('folders', {}).items():
                if 'zip_id' not in dd: continue
                grouped[dd['zip_id']]['folders'][dp] = dd

        for zip_id, summary in self._store.get('filtered_zip_data', {}).items():
            for fp, fd in summary.get('files', {}).items():
                grouped[zip_id]['files'][fp if fp[0] != '|' else fp[1:]] = fd
            for dp, dd in summary.get('folders', {}).items():
                grouped[zip_id]['folders'][dp if dp[0] != '|' else dp[1:]] = dd

        for zip_id, data in grouped.items():
            zip_data = self._store.get('zips', {}).get(zip_id, {})
            data['hash'] = zip_data.get('summary_file', {}).get('hash', NO_HASH_IN_STORE_CODE)
            is_pext = 'target_folder_path' in zip_data and zip_data['target_folder_path'].startswith('|')
            if not is_pext:
                continue
            data['files'] = {'|' + f: d for f, d in data['files'].items()}
            data['folders'] = {'|' + f: d for f, d in data['folders'].items()}

        return grouped

    @property
    def zips(self) -> Dict[str, Dict[str, Any]]:
        return self._store['zips']

    @property
    def files(self) -> Dict[str, Dict[str, Any]]:
        return self._store['files']

    def all_files(self):
        if not 'external' in self._store:
            return self._store['files']

        return ChainMap(self._store['files'], *[external['files'] for external in self._store['external'].values() if 'files' in external])

    @property
    def folders(self) -> Dict[str, Dict[str, Any]]:
        return self._store['folders']

    def all_folders(self):
        if not 'external' in self._store:
            return self._store['folders']

        return ChainMap(self._store['folders'], *[external['folders'] for external in self._store['external'].values() if 'folders' in external])

    @property
    def has_externals(self) -> bool:
        return 'external' in self._store

    @property
    def external_drives(self) -> List[str]:
        return list(self._store['external'])

    @property
    def base_path(self):
        return self._store[K_BASE_PATH]

    def has_base_path(self):
        return K_BASE_PATH in self._store

    def list_other_drives_for_file(self, file_path: str, drive: Optional[str]) -> List[Tuple[bool, str]]:
        if drive is None: drive = self.base_path
        if 'external' in self._store:
            result = [
                (True, external_drive)
                for external_drive, external in self._store['external'].items()
                if external_drive != drive and 'files' in external and file_path in external['files']
            ]
        else:
            result = []

        if drive != self.base_path and file_path in self._store['files']:
            result.append((False, self.base_path))

        return result

    def list_other_drives_for_folder(self, folder_pkg: PathPackage) -> List[Tuple[bool, str]]:
        folder_path, drive = folder_pkg.rel_path, folder_pkg.drive
        if 'external' in self._store:
            result = [
                (True, external_drive)
                for external_drive, external in self._store['external'].items()
                if external_drive != drive and 'folders' in external and folder_path in external['folders']
            ]
        else:
            result = []

        if drive != self.base_path and folder_path in self._store['folders']:
            result.append((False, self.base_path))

        return result

def equal_descriptions(lhs: dict[str, Any], b: dict[str, Any], ty: PathType) -> bool:
    if ty == PathType.FOLDER: return equal_dicts_or_lhs_bigger(lhs, b)
    else: return equal_dicts(lhs, b)

def equal_dicts_or_lhs_bigger(lhs: dict[str, Any], b: dict[str, Any]) -> bool:
    if len(b) > len(lhs):
        return False

    for key, value in lhs.items():
        if key not in b:
            continue

        if not equal_values(value, b[key]):
            return False

    return True


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

