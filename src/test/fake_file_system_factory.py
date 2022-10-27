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
import re
from pathlib import Path

from downloader.config import AllowDelete
from downloader.constants import K_BASE_PATH, K_ALLOW_DELETE, STORAGE_PATHS_PRIORITY_SEQUENCE
from downloader.file_system import FileSystemFactory as ProductionFileSystemFactory, FileSystem as ProductionFileSystem, \
    absolute_parent_folder, is_windows
from downloader.other import ClosableValue, UnreachableException
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
    def __init__(self, state=None, write_records=None):
        self._state = state if state is not None else FileSystemState()
        self._fake_failures = {}
        self._write_records = write_records if write_records is not None else []

    def create_for_config(self, config):
        return _FileSystem(self._state, config, self._fake_failures, self._write_records)

    def create_for_system_scope(self):
        return _FileSystem(self._state, self._state.config, self._fake_failures, self._write_records)

    @property
    def data(self):
        data = self._state.__dict__.copy()
        del data['config']
        del data['path_dictionary']
        return data

    @property
    def records(self):
        return [record.__dict__.copy() for record in self._write_records]

    @staticmethod
    def from_state(files=None, folders=None, config=None, base_path=None, path_dictionary=None):
        return FileSystemFactory(state=FileSystemState(files=files, folders=folders, config=config, base_path=base_path, path_dictionary=path_dictionary))


class _FileSystem(ProductionFileSystem):
    unique_temp_filename_index = 0

    def __init__(self, state, config, fake_failures, write_records):
        self._state = state
        self._config = config
        self._fake_failures = fake_failures
        self._write_records = write_records
        self._current_temp_file_index = 0

    @property
    def write_records(self):
        return [r.__dict__ for r in self._write_records]

    @property
    def data(self):
        data = self._state.__dict__.copy()
        del data['config']
        del data['path_dictionary']
        return data

    def _fix_paths(self, paths):
        return [p.replace(self._base_path(p) + '/', '') for p in paths]

    def unique_temp_filename(self):
        name = '/tmp/unique_temp_filename_%d' % self.unique_temp_filename_index
        self.unique_temp_filename_index += 1
        self._write_records.append(_Record('unique_temp_filename', name))
        return ClosableValue(name, lambda: True)

    def hash(self, path):
        return self._state.files[self._path(path)]['hash']

    def resolve(self, path):
        return self._path(path)

    def is_file(self, path):
        return self._path(path) in self._state.files

    def is_folder(self, path):
        path = self._path(path)
        if path in self._state.folders:
            return True

        entries = tuple(self._state.files) + tuple(self._state.folders)

        return path in STORAGE_PATHS_PRIORITY_SEQUENCE and any(entry.lower().startswith(path) for entry in entries)

    def read_file_contents(self, path):
        return self._state.files[self._path(path)]['content']

    def write_file_contents(self, path, content):
        if self._path(path) not in self._state.files:
            self.touch(path)
        file = self._path(path)
        self._write_records.append(_Record('write_file_contents', (file, content)))
        self._state.files[file]['content'] = content

    def touch(self, path):
        file = self._path(path)
        self._write_records.append(_Record('touch', file))
        self._state.files[file] = {'hash': path, 'size': 1}

    def set_copy_buggy(self):
        self._fake_failures['copy_buggy'] = True

    def move(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        self._state.files[target_file] = self._state.files[source_file]
        self._state.files.pop(source_file)
        self._write_records.append(_Record('move', (source_file, target_file)))

    def copy(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        source_description = self._state.files[source_file]
        if 'copy_buggy' in self._fake_failures:
            source_description['hash'] = 'buggy'

        self._state.files[target_file] = source_description
        self._write_records.append(_Record('copy', (source_file, target_file)))

    def copy_fast(self, source, target):
        self.copy(source, target)

    def make_dirs(self, path):
        folder = self._path(path)
        self._state.folders[folder] = {}
        self._write_records.append(_Record('make_dirs', folder))

    def make_dirs_parent(self, path):
        path_object = Path(self._path(path))
        if len(path_object.parents) <= 3:
            return
        parent = self._path(str(path_object.parent))
        self._state.folders[parent] = {}
        self._write_records.append(_Record('make_dirs_parent', parent))

    def _parent_folder(self, path):
        return absolute_parent_folder(self._path(path))

    def folder_has_items(self, path):
        path = self._path(path)
        for p in self._state.files:
            if path in p:
                return True

        for p in self._state.folders:
            if path in p and p != path:
                return True

        return False

    def folders(self):
        return list(self._state.folders)

    def remove_folder(self, path):
        folder = self._path(path)
        if folder in self._state.folders:
            self._state.folders.pop(folder)
        self._write_records.append(_Record('make_dirs', folder))

    def remove_non_empty_folder(self, folder_path):
        path = self._path(folder_path)
        for folder_path in list(self._state.folders):
            if folder_path.startswith(path):
                self._state.folders.pop(folder_path)

        for file_path in list(self._state.files):
            if file_path.startswith(path):
                self._state.files.pop(file_path)

    def download_target_path(self, path):
        return self._path(path)

    def unlink(self, path, verbose=True):
        file = self._path(path)
        if file in self._state.files:
            self._state.files.pop(file)
            self._write_records.append(_Record('unlink', file))
            return True
        else:
            return False

    def delete_previous(self, file):
        if self._config[K_ALLOW_DELETE] != AllowDelete.ALL:
            return True

        if not self.is_folder(self._parent_folder(file)):
            return

        regex = re.compile("^(.+_)[0-9]{8}([.][a-zA-Z0-9]+)$", )
        m = regex.match(Path(file).name)
        if m is None:
            return

        g = m.groups()
        if g is None:
            return

        start = g[0].lower()
        ext = g[1].lower()

        for file in list(self._state.files):
            name = Path(file).name
            if name.startswith(start) and name.endswith(ext) and regex.match(name):
                self._state.files.pop(file)
                self._write_records.append(_Record('delete_previous', file))

    def load_dict_from_file(self, path, suffix=None):
        file_description = self._state.files[self._path(path)]
        if 'unzipped_json' in file_description:
            return file_description['unzipped_json']
        elif 'json' in file_description:
            return file_description['json']
        else:
            raise UnreachableException('Should not reach this!')

    def save_json_on_zip(self, db, path):
        if self._path(path) not in self._state.files:
            self.touch(path)
        file = self._path(path)
        self._state.files[file]['unzipped_json'] = db
        self._write_records.append(_Record('save_json_on_zip', file))

    def save_json(self, db, path):
        if self._path(path) not in self._state.files:
            self.touch(path)
        file = self._path(path)
        self._state.files[file]['json'] = db
        self._write_records.append(_Record('save_json', file))

    def unzip_contents(self, file_path, zip_target_path, contained_files):
        contents = self._state.files[self._path(file_path)]['zipped_files']
        for file, description in contents['files'].items():
            self._state.files[self._path(file)] = {'hash': description['hash'], 'size': description['size']}
        for folder in contents['folders']:
            if not self._is_folder_unziped(contained_files, folder):
                continue

            self._state.folders[self._path(folder)] = {}

    def _is_folder_unziped(self, contained_files, folder):
        for file in contained_files:
            if folder in file:
                return True

        return False

    def _path(self, path):
        if is_windows:
            path = path.replace('\\', '/')
            if len(path) > 2 and path[0].lower() == 'c' and path[1] == ':' and path[2] == '/':
                path = path[2:]

        path = path.lower()

        if path[0] == '/':
            return path

        if path in self._state.path_dictionary:
            return '%s/%s' % (self._state.path_dictionary[path], path)

        return ('%s/%s' % (self._base_path(path), path))

    def _base_path(self, path):
        return self._config[K_BASE_PATH]


class _Record:
    def __init__(self, scope, data):
        self.scope = scope
        self.data = [d for d in data] if isinstance(data, tuple) else data


class _FakeTempFile:
    def __init__(self, name):
        self.name = name

    def close(self):
        pass
