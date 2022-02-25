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
import re
from pathlib import Path

from downloader.config import AllowDelete
from downloader.constants import FILE_MiSTer, K_BASE_PATH, K_ALLOW_DELETE, K_BASE_SYSTEM_PATH
from downloader.file_system import FileSystemFactory as ProductionFileSystemFactory, FileSystem as ProductionFileSystem
from downloader.other import ClosableValue
from test.objects import file_a, file_a_descr, file_mister_descr, hash_MiSTer_old, file_test_json_zip, \
    file_test_json_zip_descr, folder_a, config_with
from test.fake_logger import NoLogger

fake_temp_file = '/tmp/temp_file'
first_fake_temp_file = '/tmp/temp_file0'


def make_production_filesystem_factory(config) -> ProductionFileSystemFactory:
    return ProductionFileSystemFactory(config, NoLogger())


def fs_data(files=None, folders=None, system_paths=None, base_path=None):
    return FileSystemFactory(files, folders, system_paths, base_path).data


def fsf_test_with_file_a_descr():
    return FileSystemFactory(files={file_a: file_a_descr()}, folders=[folder_a])


class FileSystemFactory:
    def __init__(self, files=None, folders=None, system_paths=None, base_path=None, config=None, write_records=None):
        self._config = config if config is not None else config_with(base_path=base_path)
        base_path = _fix_base_path(self._config[K_BASE_PATH])

        self.data = {
            'files': _fs_paths(files, base_path) if files is not None else {},
            'folders': _fs_folders(folders, base_path) if folders is not None else {},
            'system_paths': _fs_system_paths(system_paths) if system_paths is not None else {}
        }
        self._fake_failures = {}
        self._write_records = write_records if write_records is not None else []

    def create_for_config(self, config):
        return _FileSystem(self.data, config, self._fake_failures, self._write_records)

    def create_for_system_scope(self):
        return _FileSystem(self.data, self._config, self._fake_failures, self._write_records)


def _fs_paths(paths, base_path):
    return {k.lower() if k[0] == '/' else (base_path + k.lower()): _clean_description(v) for k, v in paths.items()}


def _fs_folders(paths, base_path):
    return {(base_path + p.lower()): {} for p in paths}


def _fix_base_path(base_path):
    return base_path + '/' if (base_path != '' and base_path[-1] != '/') else base_path


def _fs_system_paths(paths):
    return {p: True for p in paths} if isinstance(paths, list) else paths


def _clean_description(description):
    result = {}
    if 'hash' in description:
        result['hash'] = description['hash']
    if 'size' in description:
        result['size'] = description['size']
    if 'unzipped_json' in description:
        result['unzipped_json'] = description['unzipped_json']
    if 'zipped_files' in description:
        result['zipped_files'] = description['zipped_files']
    return result


class _TestDataFileSystem:
    def __init__(self, files, folders, system_paths, config):
        self._files = files
        self._folders = folders
        self._system_paths = system_paths
        self._config = config

    def with_file(self, file, description_input):
        description = {
            'hash': description_input['hash'] if 'hash' in description_input else file,
            'size': description_input['size'] if 'size' in description_input else 1
        }
        if 'unzipped_json' in description_input:
            description['unzipped_json'] = description_input['unzipped_json']
        if 'zipped_files' in description_input:
            description['zipped_files'] = description_input['zipped_files']
        if 'content' in description_input:
            description['content'] = description_input['content']

        self._files.add(self._path(file), description)
        return self

    def with_folders(self, folders):
        for f in folders:
            self._folders.add(self._path(f), True)
        return self

    def with_folder_a(self):
        return self.with_folders([folder_a])

    def with_file_a(self, description=None):
        self.with_file(file_a, description if description is not None else file_a_descr())
        return self.with_folder_a()

    def with_mister_binary(self, description=None):
        return self.with_file(FILE_MiSTer, description if description is not None else file_mister_descr())

    def with_old_mister_binary(self):
        return self.with_mister_binary({'hash': hash_MiSTer_old})

    def with_test_json_zip(self, description=None):
        return self.with_file(file_test_json_zip, description if description is not None else file_test_json_zip_descr())

    def _path(self, path):
        if path.startswith('/'):
            return path
        return ('%s/%s' % (self._base_path(path), path)).replace('//', '/')

    def _base_path(self, path):
        return self._config[K_BASE_SYSTEM_PATH] if path in self._system_paths else self._config[K_BASE_PATH]


class _FileSystem(ProductionFileSystem):
    unique_temp_filename_index = 0

    def __init__(self, data, config, fake_failures, write_records):
        self.data = data
        self._config = config
        self._fake_failures = fake_failures
        self._write_records = write_records
        self._current_temp_file_index = 0

    @property
    def test_data(self) -> _TestDataFileSystem:
        files = _CaseInsensitiveDict(self.data['files'])
        folders = _CaseInsensitiveDict(self.data['folders'])
        return _TestDataFileSystem(files, folders, self.data['system_paths'], self._config)

    @property
    def write_records(self):
        return [r.__dict__ for r in self._write_records]

    def _fix_paths(self, paths):
        return [p.replace(self._base_path(p) + '/', '') for p in paths]

    def temp_file(self):
        result = fake_temp_file + str(self._current_temp_file_index)
        self._current_temp_file_index += 1
        self._write_records.append(_Record('temp_file', result))
        return _FakeTempFile(result)

    def unique_temp_filename(self):
        name = 'unique_temp_filename_%d' % self.unique_temp_filename_index
        self.unique_temp_filename_index += 1
        self._write_records.append(_Record('unique_temp_filename', name))
        return ClosableValue(name, lambda: True)

    def hash(self, path):
        return self.data['files'][self._path(path)]['hash']

    def resolve(self, path):
        return self._path(path)

    def add_system_path(self, path):
        self._write_records.append(_Record('add_system_path', path))
        self.data['system_paths'][path] = True

    def is_file(self, path):
        return self._path(path) in self.data['files']

    def is_folder(self, path):
        return self._path(path) in self.data['folders']

    def read_file_contents(self, path):
        return self.data['files'][self._path(path)]['content']

    def write_file_contents(self, path, content):
        if self._path(path) not in self.data['files']:
            self.touch(path)
        file = self._path(path)
        self._write_records.append(_Record('write_file_contents', (file, content)))
        self.data['files'][file]['content'] = content

    def touch(self, path):
        file = self._path(path)
        self._write_records.append(_Record('touch', file))
        self.data['files'][file] = {'hash': path, 'size': 1}

    def set_copy_buggy(self):
        self._fake_failures['copy_buggy'] = True

    def move(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        self.data['files'][target_file] = self.data['files'][source_file]
        self.data['files'].pop(source_file)
        self._write_records.append(_Record('move', (source_file, target_file)))

    def copy(self, source, target):
        source_file = self._path(source)
        target_file = self._path(target)
        source_description = self.data['files'][source_file]
        if 'copy_buggy' in self._fake_failures:
            source_description['hash'] = 'buggy'

        self.data['files'][target_file] = source_description
        self._write_records.append(_Record('copy', (source_file, target_file)))

    def copy_fast(self, source, target):
        self.copy(source, target)

    def make_dirs(self, path):
        folder = self._path(path)
        self.data['folders'][folder] = {}
        self._write_records.append(_Record('make_dirs', folder))

    def make_dirs_parent(self, path):
        parent = str(Path(self._path(path)).parent)
        if parent == self._base_path(path) or parent == '/tmp':
            return
        self.data['folders'][parent] = {}
        self._write_records.append(_Record('make_dirs_parent', parent))

    def folder_has_items(self, path):
        path = self._path(path)
        for p in self.data['files']:
            if p in path:
                return True

        for p in self.data['folders']:
            if p in path and p != path:
                return True

        return False

    def folders(self):
        return list(self.data['folders'])

    def remove_folder(self, path):
        folder = self._path(path)
        self.data['folders'].pop(folder)
        self._write_records.append(_Record('make_dirs', folder))

    def download_target_path(self, path):
        return self._path(path)

    def unlink(self, path, verbose=True):
        file = self._path(path)
        self.data['files'].pop(file)
        self._write_records.append(_Record('unlink', file))

    def delete_previous(self, file):
        if self._config[K_ALLOW_DELETE] != AllowDelete.ALL:
            return True

        path = Path(self._path(file))
        if not self.is_folder(str(path.parent)):
            return

        regex = re.compile("^(.+_)[0-9]{8}([.][a-zA-Z0-9]+)$", )
        m = regex.match(path.name)
        if m is None:
            return

        g = m.groups()
        if g is None:
            return

        start = g[0].lower()
        ext = g[1].lower()

        for file in list(self.data['files']):
            name = Path(file).name
            if name.startswith(start) and name.endswith(ext) and regex.match(name):
                self.data['files'].pop(file)
                self._write_records.append(_Record('delete_previous', file))

    def load_dict_from_file(self, path, suffix=None):
        return self.data['files'][self._path(path)]['unzipped_json']

    def save_json_on_zip(self, db, path):
        if self._path(path) not in self.data['files']:
            self.touch(path)
        file = self._path(path)
        self.data['files'][file]['unzipped_json'] = db
        self._write_records.append(_Record('save_json_on_zip', file))

    def unzip_contents(self, file_path, zip_target_path, contained_files):
        contents = self.data['files'][self._path(file_path)]['zipped_files']
        for file, description in contents['files'].items():
            self.data['files'][self._path(file)] = {'hash': description['hash'], 'size': description['size']}
        for folder in contents['folders']:
            if not self._is_folder_unziped(contained_files, folder):
                continue

            self.data['folders'][self._path(folder)] = {}

    def _is_folder_unziped(self, contained_files, folder):
        for file in contained_files:
            if folder in file:
                return True

        return False

    def _path(self, path):
        if path[0] == '/':
            return path.lower()

        return ('%s/%s' % (self._base_path(path), path)).lower()

    def _base_path(self, path):
        return self._config[K_BASE_SYSTEM_PATH] if path in self.data['system_paths'] else self._config[K_BASE_PATH]


class _Record:
    def __init__(self, scope, data):
        self.scope = scope
        self.data = data


class _FakeTempFile:
    def __init__(self, name):
        self.name = name

    def close(self):
        pass


class _CaseInsensitiveDict:
    def __init__(self, d=None):
        self._dict = dict() if d is None else d

    def add(self, key, value):
        self._dict[key.lower()] = value

    def get(self, key):
        return self._dict[key.lower()]

    def has(self, key):
        return key.lower() in self._dict

    def pop(self, key):
        self._dict.pop(key.lower())

    def keys(self):
        return self._dict.keys()
