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
from typing import List, Set
import pathlib
from downloader.constants import file_MiSTer
from downloader.file_system import FileSystem as ProductionFileSystem
from downloader.other import ClosableValue
from test.objects import file_a, file_a_descr, file_mister_descr, hash_MiSTer_old, file_test_json_zip, \
    file_test_json_zip_descr, folder_a
from test.fake_logger import NoLogger

fake_temp_file = '/tmp/temp_file'
first_fake_temp_file = '/tmp/temp_file0'


class TestDataFileSystem:
    def __init__(self, files, folders, base_path):
        self._files = files
        self._folders = folders
        self._base_path = base_path

    def with_file(self, file, description):
        self._files.add(self._path(file), description)
        return self

    def with_folders(self, folders):
        for f in folders:
            self._folders.add(self._path(f), True)
        return self

    def with_folder_a(self):
        return self.with_folders([folder_a])

    def with_file_a(self, description=None):
        self._files.add(self._path(file_a), description if description is not None else file_a_descr())
        return self.with_folder_a()

    def with_mister_binary(self, description=None):
        self._files.add(self._path(file_MiSTer), description if description is not None else file_mister_descr())

    def with_old_mister_binary(self):
        self.with_mister_binary({'hash': hash_MiSTer_old})

    def with_test_json_zip(self, description=None):
        self._files.add(self._path(file_test_json_zip), description if description is not None else file_test_json_zip_descr())
        return self

    def _path(self, path):
        if path.startswith('/'):
            return path
        return ('%s/%s' % (self._base_path, path)).replace('//', '/')


def make_production_filesystem(config) -> ProductionFileSystem:
    return ProductionFileSystem(config, NoLogger())


class FakeTempFile:
    def __init__(self, name):
        self.name = name

    def close(self):
        pass


class FakeFileSystemFactory:
    def __init__(self):
        self.file_systems = dict()
        self._common_files = CaseInsensitiveDict()
        self._common_folders = CaseInsensitiveDict()

    def create_for_base_path(self, config, base_path):
        if base_path not in self.file_systems:
            fs_config = config.copy()
            fs_config['base_path'] = base_path
            self.file_systems[base_path] = FileSystem(fs_config, self._common_files, self._common_folders)
        return self.file_systems[base_path]


class StubFileSystemFactory:
    def __init__(self, file_system):
        self._file_system = file_system

    def create_for_config(self, _):
        return self._file_system

    def create_for_db_id(self, _):
        return self._file_system


class FileSystem(ProductionFileSystem):
    unique_temp_filename_index = 0

    def __init__(self, config=None, common_files=None, common_folders=None):
        self._files = CaseInsensitiveDict() if common_files is None else common_files
        self._folders = CaseInsensitiveDict() if common_folders is None else common_folders
        self._system_paths = list()
        self._removed_files = list()
        self._removed_folders = list()
        self._current_temp_file_index = 0
        self._base_path = '/media/fat/' if config is None else config['base_path']
        self._historic_paths = set()
        self._copy_buggy = False

    @property
    def test_data(self) -> TestDataFileSystem:
        return TestDataFileSystem(self._files, self._folders, self._base_path)

    @property
    def system_paths(self) -> List[str]:
        return self._system_paths.copy()

    @property
    def removed_files(self) -> List[str]:
        return self._fix_paths(self._removed_files)

    @property
    def removed_folders(self) -> List[str]:
        return self._fix_paths(self._removed_folders)

    @property
    def historic_paths(self) -> List[str]:
        return self._fix_paths(self._historic_paths)

    def add_system_path(self, path):
        self._system_paths.append(path)

    def resolve(self, path):
        return self._path(path)

    def temp_file(self):
        result = fake_temp_file + str(self._current_temp_file_index)
        self._current_temp_file_index += 1
        self._historic_paths.add(result)
        return FakeTempFile(result)

    def unique_temp_filename(self):
        name = 'unique_temp_filename_%d' % self.unique_temp_filename_index
        self.unique_temp_filename_index += 1
        return ClosableValue(name, lambda: True)

    def is_file(self, path):
        return self._files.has(self._path(path))

    def is_folder(self, path):
        return self._folders.has(self._path(path))

    def read_file_contents(self, path):
        if not self._files.has(self._path(path)):
            return 'unknown'
        return self._files.get(self._path(path))['content']

    def write_file_contents(self, path, content):
        if not self._files.has(self._path(path)):
            self._files.add(self._path(path), {})
        self._files.get(self._path(path))['content'] = content
        self._historic_paths.add(self._path(path))

    def touch(self, path):
        self._files.add(self._path(path), {'hash': path})
        self._historic_paths.add(self._path(path))

    def move(self, source, target):
        description = self._files.get(self._path(source))
        self._files.add(self._path(target), description)
        self._files.pop(self._path(source))
        self._historic_paths.add(self._path(source))
        self._historic_paths.add(self._path(target))

    def set_copy_buggy(self):
        self._copy_buggy = True

    def copy(self, source, target):
        source_description = self._files.get(self._path(source))
        if self._copy_buggy:
            source_description['hash'] = 'buggy'

        self._files.add(self._path(target), source_description)
        self._historic_paths.add(self._path(source))
        self._historic_paths.add(self._path(target))

    def copy_fast(self, source, target):
        self.copy(source, target)

    def hash(self, path):
        return self._files.get(self._path(path))['hash']

    def make_dirs(self, path):
        self._folders.add(self._path(path), True)

    def make_dirs_parent(self, path):
        self._folders.add(str(pathlib.Path(self._path(path)).parent), True)

    def folder_has_items(self, path):
        path = self._path(path).lower()
        for folder in self._folders.keys():
            if folder != path and folder.startswith(path):
                return True
        path = path + '/'
        for file in self._files.keys():
            if file.startswith(path):
                return True
        return False

    def folders(self):
        return self._fix_paths(sorted(self._folders.keys()))

    def _fix_paths(self, paths):
        return [p.replace(self._base_path, '') for p in paths]

    def remove_folder(self, path):
        self._folders.pop(self._path(path))
        self._removed_folders.append(self._path(path))

    def download_target_path(self, path):
        return self._path(path)

    def _path(self, path):
        if path.startswith('/'):
            return path
        return ('%s/%s' % (self._base_path, path)).replace('//', '/')

    def unlink(self, path, verbose=True):
        if self._files.has(self._path(path)):
            self._files.pop(self._path(path))
            self._removed_files.append(self._path(path))

    def delete_previous(self, file):
        pass

    def save_json_on_zip(self, db, path):
        pass

    def load_dict_from_file(self, path, suffix=None):
        file_description = self._files.get(self._path(path))
        unzipped_json = file_description['unzipped_json']
        file_description.pop('unzipped_json')
        return unzipped_json

    def unzip_contents(self, file, target):
        file_description = self._files.get(self._path(file))
        for path in file_description['zipped_files']['folders']:
            self._folders.add(self._path(path), {})
        for path, description in file_description['zipped_files']['files'].items():
            self._files.add(self._path(path), description)
        file_description.pop('zipped_files')


class CaseInsensitiveDict:
    def __init__(self):
        self._dict = dict()

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
