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
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from downloader.constants import STORAGE_PATHS_PRIORITY_SEQUENCE, HASH_file_does_not_exist
from downloader.file_system import FileSystemFactory as ProductionFileSystemFactory, FileSystem as ProductionFileSystem, \
    FsError, UnzipError, \
    absolute_parent_folder, FolderCreationError, FsSharedState, FileCopyError, FileReadError
from downloader.path_package import PathPackage
from test.fake_http_gateway import FakeBuf
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_logger import NoLogger

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

    def are_files(self, file_pkgs: List[PathPackage]) -> Tuple[List[PathPackage], List[PathPackage]]:
        are = []
        nope = []
        for p in file_pkgs:
            if self.is_file(p.full_path): are.append(p)
            else: nope.append(p)
        return are, nope

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

    def read_file_bytes(self, path: str) -> io.BytesIO:
        return FakeBuf(self.state.files[self._path(path)])

    def precache_is_file_with_folders(self, _folders: list[str], recheck: bool = False):
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

    def set_read_error(self):
        self._fake_failures['read_error'] = True

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

    def make_dirs(self, path):
        folder = self._path(path)
        path_parents = list(Path(folder).parents)
        for p in path_parents[:-3]:
            parent = str(p)
            if parent not in self.state.folders:
                self.state.folders[parent] = {}
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

    def write_incoming_stream(self, in_stream: Any, target_path: str, timeout: int, /) -> tuple[int, str]:
        if in_stream.storing_problems:
            return 0, ''

        lower_path = target_path.lower()
        self._write_records.append(_Record('write_incoming_stream', lower_path))
        self.state.files[lower_path] = in_stream.description
        self._fs_cache.add_file(lower_path)
        return self.size(lower_path), self.hash(lower_path)

    def write_stream_to_data(self, in_stream: Any, calc_md5: bool, timeout: int, /) -> Tuple[io.BytesIO, str]:
        if in_stream.storing_problems:
            return

        return in_stream.buf, in_stream.description['hash'] if calc_md5 else ''

    def unlink(self, path, verbose=True):
        full_path = self._path(path)
        if full_path in self.state.files:
            self.state.files.pop(full_path)
            self._write_records.append(_Record('unlink', full_path))
            self._fs_cache.remove_file(full_path)
            return True
        else:
            return False

    def load_dict_from_transfer(self, source: str, transfer: Union[str, io.BytesIO]):
        if isinstance(transfer, str):
            path = self._path(transfer)
            result = self.load_dict_from_file(path)
            self.state.files.pop(path)
            return result
        else: return self._load_dict_from_data(source, transfer)

    def load_dict_from_file(self, path):
        if 'read_error' in self._fake_failures:
            raise FileReadError(path)

        full_path = self._path(path)
        file_description = self.state.files[full_path]
        return self._load_json_from_description(path, file_description)

    def _load_dict_from_data(self, source: str, data: io.BytesIO) -> Dict[str, Any]:
        if not isinstance(data, FakeBuf): raise FsError('This should have been a FakeBuf.')
        return self._load_json_from_description(source, data.description)

    def _load_json_from_description(self, info: str, description: Dict[str, Any]) -> Any:
        if 'unzipped_json' in description:
            return description['unzipped_json']
        elif 'json' in description:
            return description['json']
        else:
            raise FsError(f'Transfer {info} does not have a json content.')

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

    def unzip_contents(self, transfer: Union[str, io.BytesIO], target_path: Union[str, Dict[str, str]], test_info: Tuple[Optional[PathPackage], List[PathPackage], Dict[str, Dict[str, Any]]]):
        if isinstance(transfer, str):
            contents = self.state.files[self._path(transfer)]['zipped_files']
            self.unlink(transfer)
        else:
            contents = transfer.description['zipped_files']

        if 'unzip_error' in self._fake_failures:
            raise UnzipError(transfer)

        target_path_by_relpath = None if isinstance(target_path, str) else target_path

        extracting = {}
        target_pkg, files_to_unzip, filtered_files = test_info
        if target_path_by_relpath is not None:
            # Should NOT extract all case
            extracting.update(target_path_by_relpath)
            if target_pkg is None:
                zip_path, full_path = next(iter(target_path_by_relpath.items()))
                abs_zip_root_path = full_path.removesuffix(zip_path)
                for f_desc in filtered_files.values():
                    f = f_desc['zip_path']
                    extracting[f] = os.path.join(abs_zip_root_path, f)
        else:
            # Should extract all case
            zip_root_path = os.path.join(target_pkg.rel_path, '')
            abs_zip_root_path = target_pkg.full_path
            for f_path in list(filtered_files) + ([pkg.rel_path for pkg in files_to_unzip] if target_path_by_relpath is None else []):
                f = f_path.lstrip('|').removeprefix(zip_root_path)
                extracting[f] = os.path.join(abs_zip_root_path, f)

        for file, description in contents['files'].items():
            full_path = extracting.get(file, None)
            if full_path is None:
                continue
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