# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from test.objects import file_a, file_a_descr, file_mister_descr, hash_MiSTer_old, file_test_json_zip, \
    file_test_json_zip_descr, folder_a
from test.fake_logger import NoLogger

fake_temp_file = '/tmp/temp_file'
first_fake_temp_file = '/tmp/temp_file0'

class TestDataFileSystem:
    def __init__(self, files, folders):
        self._files = files
        self._folders = folders

    def with_file(self, file, description):
        self._files.add(file, description)
        return self

    def with_folders(self, folders):
        for f in folders:
            self._folders.add(f, True)
        return self

    def with_folder_a(self):
        return self.with_folders([folder_a])

    def with_file_a(self, description=None):
        self._files.add(file_a, description if description is not None else file_a_descr())
        return self.with_folder_a()

    def with_mister_binary(self, description=None):
        self._files.add(file_MiSTer, description if description is not None else file_mister_descr())

    def with_old_mister_binary(self):
        self.with_mister_binary({'hash': hash_MiSTer_old})

    def with_test_json_zip(self, description=None):
        self._files.add(file_test_json_zip, description if description is not None else file_test_json_zip_descr())
        return self


def make_production_filesystem(config) -> ProductionFileSystem:
    return ProductionFileSystem(config, NoLogger())


class FakeTempFile:
    def __init__(self, name):
        self.name = name

    def close(self):
        pass

class FileSystem(ProductionFileSystem):
    def __init__(self, target_path_prefix=''):
        self._files = CaseInsensitiveDict()
        self._folders = CaseInsensitiveDict()
        self._system_paths = list()
        self._removed_files = list()
        self._removed_folders = list()
        self._current_temp_file_index = 0
        self._target_path_prefix = target_path_prefix
        self._historic_paths = set()

    @property
    def test_data(self) -> TestDataFileSystem:
        return TestDataFileSystem(self._files, self._folders)

    @property
    def system_paths(self) -> List[str]:
        return self._system_paths.copy()

    @property
    def removed_files(self) -> List[str]:
        return self._removed_files

    @property
    def removed_folders(self) -> List[str]:
        return self._removed_folders

    @property
    def historic_paths(self) -> Set[str]:
        return self._historic_paths

    def add_system_path(self, path):
        self._system_paths.append(path)

    def resolve(self, path):
        return path

    def temp_file(self):
        result = fake_temp_file + str(self._current_temp_file_index)
        self._current_temp_file_index += 1
        self._historic_paths.add(result)
        return FakeTempFile(result)

    def is_file(self, path):
        return self._files.has(path)

    def is_folder(self, path):
        return self._folders.has(path)

    def read_file_contents(self, path):
        if not self._files.has(path):
            return 'unknown'
        return self._files.get(path)['content']

    def write_file_contents(self, path, content):
        if not self._files.has(path):
            self._files.add(path, {})
        self._files.get(path)['content'] = content
        self._historic_paths.add(path)

    def touch(self, path):
        self._files.add(path, {'hash': path})
        self._historic_paths.add(path)

    def move(self, source, target):
        description = self._files.get(source)
        self._files.add(target, description)
        self._files.pop(source)
        self._historic_paths.add(source)
        self._historic_paths.add(target)

    def copy(self, source, target):
        self._files.add(target, self._files.get(source))
        self._historic_paths.add(source)
        self._historic_paths.add(target)

    def hash(self, path):
        return self._files.get(path)['hash']

    def make_dirs(self, path):
        self._folders.add(path, True)

    def make_dirs_parent(self, path):
        self._folders.add(str(pathlib.Path(path).parent), True)

    def folder_has_items(self, path):
        path = path.lower()
        for folder in self._folders.keys():
            if folder != path and folder.startswith(path):
                return True
        path = path + '/'
        for file in self._files.keys():
            if file.startswith(path):
                return True
        return False

    def folders(self):
        return list(sorted(self._folders.keys()))

    def remove_folder(self, path):
        self._folders.pop(path)
        self._removed_folders.append(path)

    def download_target_path(self, path):
        if path.startswith('/tmp/'):
            return path
        return self._target_path_prefix + path

    def unlink(self, path):
        if self._files.has(path):
            self._files.pop(path)
            self._removed_files.append(path)

    def delete_previous(self, file):
        pass

    def save_json_on_zip(self, db, path):
        pass

    def load_dict_from_file(self, path, suffix=None):
        file_description = self._files.get(path)
        unzipped_json = file_description['unzipped_json']
        file_description.pop('unzipped_json')
        return unzipped_json

    def unzip_contents(self, file, target):
        file_description = self._files.get(file)
        for path in file_description['zipped_files']['folders']:
            self._folders.add(path, {})
        for path, description in file_description['zipped_files']['files'].items():
            self._files.add(path, description)
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
