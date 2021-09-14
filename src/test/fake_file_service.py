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
import test.objects


class TestDataFileService:
    def __init__(self, files):
        self._files = files

    def with_file(self, file, description):
        self._files.add(file, description)
        return self

    def with_file_a(self, description=None):
        self._files.add(test.objects.file_a, description if description is not None else test.objects.file_a_descr())
        return self

    def with_test_json_zip(self, description=None):
        self._files.add(test.objects.file_test_json_zip, description if description is not None else test.objects.file_test_json_zip_descr())
        return self


class FileService:
    def __init__(self):
        self._files = CaseInsensitiveDict()

    @property
    def test_data(self):
        return TestDataFileService(self._files)

    def add_system_path(self, path):
        pass

    def is_file(self, path):
        return self._files.has(path)

    def read_file_contents(self, path):
        if not self._files.has(path):
            return 'unknown'
        return self._files.get(path)['content']

    def write_file_contents(self, path, content):
        if not self._files.has(path):
            self._files.add(path, {})
        self._files.get(path)['content'] = content

    def touch(self, path):
        self._files.add(path, {'hash': path})

    def move(self, source, target):
        self._files.add(target, {'hash': target})
        self._files.pop(source)

    def copy(self, source, target):
        self._files.add(target, self._files.get(source))

    def hash(self, path):
        return self._files.get(path)['hash']

    def makedirs(self, path):
        pass

    def makedirs_parent(self, path):
        pass

    def curl_target_path(self, path):
        return path

    def unlink(self, path):
        if self._files.has(path):
            self._files.pop(path)

    def clean_expression(self, expr):
        if expr[-1:] == '*':
            pass
        else:
            self.unlink(expr)

    def save_json_on_zip(self, db, path):
        pass

    def load_db_from_file(self, path):
        return self._files.get(path)['unzipped_json']


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
