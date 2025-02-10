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
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from downloader.constants import K_BASE_PATH, STORAGE_PATHS_PRIORITY_SEQUENCE, HASH_file_does_not_exist
from downloader.file_system import FileSystemFactory as ProductionFileSystemFactory, FileSystem as ProductionFileSystem, FsError, UnzipError, \
    absolute_parent_folder, is_windows, FolderCreationError, FsSharedState, FileCopyError
from downloader.other import ClosableValue
from downloader.path_package import PathPackage
from test.fake_importer_implicit_inputs import FileSystemState
from downloader.logger import NoLogger

first_fake_temp_file = '/tmp/unique_temp_filename_0'


def make_production_filesystem_factory(config, path_dictionary=None) -> ProductionFileSystemFactory:
    return ProductionFileSystemFactory(config, path_dictionary or {}, NoLogger())


def fs_data(files=None, folders=None, base_path=None):
    return FileSystemFactory(state=FileSystemState(files, folders, base_path)).data


def fs_records(records):
    return json.loads(json.dumps(records).lower())


class FileSystemFactory:
    def __init__(self, state=None, write_records=None, config=None):
        self._state = state if state is not None else FileSystemState(config=config)
        self._fake_failures = {}
        self._write_records = write_records if write_records is not None else []
        self._fs_cache = FsSharedState()

    def set_create_folders_will_error(self):
        self._fake_failures['create_folders_error'] = True

    def set_copy_will_error(self):
        self._fake_failures['copy_error'] = True

    def set_unzip_will_error(self):
        self._fake_failures['unzip_error'] = True

    def create_for_config(self, config):
        return FakeFileSystem(self._state, config, self._fake_failures, self._write_records, self._fs_cache)

    def create_for_system_scope(self):
        return FakeFileSystem(self._state, self._state.config, self._fake_failures, self._write_records, self._fs_cache)

    @property
    def data(self):
        return fs_state_to_data(self._state)

    @property
    def private_state(self): return self._state

    @property
    def records(self):
        return [record.__dict__.copy() for record in self._write_records if record.not_ignored()]

    @staticmethod
    def from_state(files=None, folders=None, config=None, base_path=None, path_dictionary=None):
        return FileSystemFactory(state=FileSystemState(files=files, folders=folders, config=config, base_path=base_path, path_dictionary=path_dictionary))


def fs_state_to_data(state: FileSystemState):
    def change_files(files): return {
        k: {
            'hash': v['hash'] if 'hash' in v else 'NO_HASH', 'size': v['size'] if 'size' in v else 1
        } for k, v in files.items()
    }
    def change_folders(folders): return {k: {} for k in folders}

    return {'files': change_files(state.files), 'folders': change_folders(state.folders)}


class FakeFileSystem(ProductionFileSystem):
    unique_temp_filename_index = 0

    def __init__(self, state, config, fake_failures, write_records, fs_cache: FsSharedState):
        self.state = state
        self._config = config
        self._fake_failures = fake_failures
        self._write_records = write_records
        self._current_temp_file_index = 0
        self._fs_cache = fs_cache

    @property
    def write_records(self):
        return [r.__dict__ for r in self._write_records]

    @property
    def data(self):
        return fs_state_to_data(self.state)

    def _fix_paths(self, paths):
        return [p.replace(self._base_path(p) + '/', '') for p in paths]

    def unique_temp_filename(self, register: bool = True):
        name = '/tmp/unique_temp_filename_%d' % self.unique_temp_filename_index
        self.unique_temp_filename_index += 1
        if register: self._write_records.append(_Record('unique_temp_filename', name))
        return ClosableValue(name, lambda: None)

    def persistent_temp_dir(self) -> str:
        return '/tmp'

    def hash(self, path):
        file_path = self._path(path)
        if file_path not in self.state.files:
            return HASH_file_does_not_exist
        return self.state.files[file_path]['hash']

    def size(self, path):
        return self.state.files[self._path(path)]['size']

    def resolve(self, path):
        return self._path(path)

    def is_file(self, path, use_cache: bool = True):
        full_path = self._path(path)
        if self._fs_cache.contains_file(full_path):
            return True

        if full_path in self.state.files:
            self._fs_cache.add_file(full_path)
            return True

        return False

    def print_debug(self):
        pass

    def is_folder(self, path):
        path = self._path(path)
        if path in self.state.folders:
            return True

        entries = tuple(self.state.files) + tuple(self.state.folders)

        return path in STORAGE_PATHS_PRIORITY_SEQUENCE and any(entry.lower().startswith(path) for entry in entries)

    def read_file_contents(self, path):
        return self.state.files[self._path(path)]['content']

    def precache_is_file_with_folders(self, folders: list[str]):
        pass

    def write_file_contents(self, path, content):
        if self._path(path) not in self.state.files:
            self.touch(path)
        file = self._path(path)
        self._write_records.append(_Record('write_file_contents', (file, content)))
        self.state.files[file]['content'] = content

    def touch(self, path):
        file = self._path(path)
        self._write_records.append(_Record('touch', file))
        self.state.files[file] = {'hash': path, 'size': 1}

    def set_copy_buggy(self):
        self._fake_failures['copy_buggy'] = True

    def move(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        if source_file not in self.state.files:
            raise Exception('Source file "%s" does not exist!' % source_file)
        self.state.files[target_file] = self.state.files[source_file]
        self.state.files.pop(source_file)
        self._write_records.append(_Record('move', (source_file, target_file)))
        self._fs_cache.add_file(target_file)
        self._fs_cache.remove_file(source_file)

    def copy(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        source_description = self.state.files[source_file]
        if 'copy_buggy' in self._fake_failures:
            source_description['hash'] = 'buggy'
        elif 'copy_error' in self._fake_failures:
            raise FileCopyError(target)

        self.state.files[target_file] = source_description
        self._write_records.append(_Record('copy', (source_file, target_file)))
        self._fs_cache.add_file(target_file)

    def copy_fast(self, source, target):
        self.copy(source, target)

    def make_dirs(self, path):
        folder = self._path(path)
        self.state.folders[folder] = {}
        self._write_records.append(_Record('make_dirs', folder))
        if 'create_folders_error' in self._fake_failures:
            raise FolderCreationError(folder)

    def make_dirs_parent(self, path):
        path_object = Path(self._path(path))
        if len(path_object.parents) <= 3:
            return
        parent = self._path(str(path_object.parent))
        self.state.folders[parent] = {}
        self._write_records.append(_Record('make_dirs_parent', parent))
        if 'create_folders_error' in self._fake_failures:
            raise FolderCreationError(parent)

    def _parent_folder(self, path):
        return absolute_parent_folder(self._path(path))

    def folder_has_items(self, path):
        path = self._path(path)
        for p in self.state.files:
            if path in p:
                return True

        for p in self.state.folders:
            if path in p and p != path:
                return True

        return False

    def folders(self):
        return list(self.state.folders)

    def remove_folder(self, path):
        folder = self._path(path)
        if folder in self.state.folders:
            for other_folder in self.state.folders:
                if other_folder.startswith(folder) and other_folder != folder:
                    raise Exception(f'Cannot remove non-empty folder {folder} because {other_folder} exists!')

            self.state.folders.pop(folder)
        self._write_records.append(_Record('make_dirs', folder))

    def remove_non_empty_folder(self, folder_path):
        path = self._path(folder_path)
        for folder_path in list(self.state.folders):
            if folder_path.startswith(path):
                self.state.folders.pop(folder_path)

        for file_path in list(self.state.files):
            if file_path.startswith(path):
                self.state.files.pop(file_path)

    def download_target_path(self, path):
        return self._path(path)

    def write_incoming_stream(self, in_stream: Any, target_path: str, timeout: int):
        if in_stream.storing_problems:
            return

        lower_path = target_path.lower()
        self._write_records.append(_Record('write_incoming_stream', lower_path))
        self.state.files[lower_path] = in_stream.description
        self._fs_cache.add_file(lower_path)

    def unlink(self, path, verbose=True):
        full_path = self._path(path)
        if full_path in self.state.files:
            self.state.files.pop(full_path)
            self._write_records.append(_Record('unlink', full_path))
            self._fs_cache.remove_file(full_path)
            return True
        else:
            return False

    def load_dict_from_file(self, path, suffix=None):
        file_description = self.state.files[self._path(path)]
        if 'unzipped_json' in file_description:
            return file_description['unzipped_json']
        elif 'json' in file_description:
            return file_description['json']
        else:
            raise FsError(f'File {path} does not have a json content.')

    def save_json_on_zip(self, db, path):
        if self._path(path) not in self.state.files:
            self.touch(path)
        file = self._path(path)
        self.state.files[file]['unzipped_json'] = db
        self._write_records.append(_Record('save_json_on_zip', file))

    def save_json(self, db, path):
        if self._path(path) not in self.state.files:
            self.touch(path)
        file = self._path(path)
        self.state.files[file]['json'] = db
        self._write_records.append(_Record('save_json', file))

    def unzip_contents(self, file_path, zip_target_path, files_to_unzip: Optional[Dict[str, str]], test_info: Tuple[Optional[PathPackage], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]):
        if 'unzip_error' in self._fake_failures:
            raise UnzipError(file_path)

        extracting = {}
        target_pkg, files, filtered_files = test_info
        if files_to_unzip is not None:
            extracting.update(files_to_unzip)
            if target_pkg is None:
                zip_path, full_path = next(iter(files_to_unzip.items()))
                abs_zip_root_path = full_path.removesuffix(zip_path)
                for f_desc in filtered_files.values():
                    f = f_desc['zip_path']
                    extracting[f] = os.path.join(abs_zip_root_path, f)

        if target_pkg is not None:
            zip_root_path = os.path.join(target_pkg.rel_path, '')
            abs_zip_root_path = target_pkg.full_path
            for f_path in list(filtered_files) + (list(files) if files_to_unzip is None else []):
                f = f_path.lstrip('|').removeprefix(zip_root_path)
                extracting[f] = os.path.join(abs_zip_root_path, f)

        contents = self.state.files[self._path(file_path)]['zipped_files']
        for file, description in contents['files'].items():
            full_path = extracting.get(file, None)
            if full_path is None:
                full_path = self._path(file)
            self.state.files[full_path.lower()] = {'hash': description['hash'], 'size': description['size']}

        for folder in contents['folders']:
            if not self._is_folder_unziped(extracting, folder):
                continue

            self.state.folders[self._path(folder)] = {}

    def turn_off_logs(self) -> None:
        pass

    def _is_folder_unziped(self, extracting: Dict[str, str], folder: str):
        for file in extracting:
            if file.lower().startswith(folder):
                return True

        return False

    def _path(self, path: str) -> str:
        if path[0] == '/' or os.path.isabs(path):
            return path.lower()

        return os.path.join(self._config['base_path'], path).lower()


class _Record:
    def __init__(self, scope, data):
        self.scope = scope
        self.data = [d for d in data] if isinstance(data, tuple) else data

    def not_ignored(self):
        if not isinstance(self.data, str): return True
        return not self.data.endswith('.test_downloader')