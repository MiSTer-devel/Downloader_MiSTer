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
from pathlib import Path

from downloader.constants import K_BASE_PATH, FILE_MiSTer, MEDIA_USB0
from test.objects import config_with, file_a, file_a_descr, hash_MiSTer_old, file_mister_descr, file_test_json_zip, \
    file_test_json_zip_descr, remove_priority_path


class NetworkState:
    def __init__(self, remote_failures=None, remote_files=None, storing_problems=None):
        self.remote_failures = dict() if remote_failures is None else remote_failures
        self.remote_files = dict() if remote_files is None else remote_files
        self.storing_problems = set() if storing_problems is None else storing_problems


class FileSystemState:
    def __init__(self, files=None, folders=None, base_path=None, config=None, path_dictionary=None, base_system_path=None):
        self.path_dictionary = path_dictionary if path_dictionary is not None else {}
        self.config = config if config is not None else config_with(base_path=base_path, base_system_path=MEDIA_USB0 if base_system_path is None else base_system_path)
        base_path = _fix_base_path(self.config[K_BASE_PATH])
        self.files = _fs_paths(files, base_path) if files is not None else {}
        self.folders = _fs_folders(folders, base_path) if folders is not None else {}

    def add_file(self, base_path, file, description):
        if base_path is None:
            base_path = self.config[K_BASE_PATH]

        if base_path is not self.config[K_BASE_PATH]:
            self.set_non_base_path(base_path, file)

        path = file.lower() if file[0] == '/' else base_path.lower() + '/' + file.lower()

        self.files[path] = self.fix_description(file, description)
        return self

    def set_non_base_path(self, base, file):
        self.path_dictionary[file.lower()] = base

    def add_full_file_path(self, path, fixed_description):
        self.files[path.lower()] = fixed_description
        return self

    def add_file_a(self, base_path=None, description=None):
        self.add_file(base_path, file_a, description if description is not None else file_a_descr())
        return self

    def add_mister_binary(self, base_path=None, description=None):
        self.add_file(base_path, FILE_MiSTer, description if description is not None else file_mister_descr())
        return self

    def add_old_mister_binary(self, base_path=None):
        self.add_mister_binary(base_path, description={'hash': hash_MiSTer_old})
        return self

    def add_test_json_zip(self, base_path=None, description=None):
        self.add_file(base_path=base_path, file=file_test_json_zip, description=description if description is not None else file_test_json_zip_descr())
        return self

    def add_folder(self, base_path, folder, description=None):
        if base_path is None:
            base_path = self.config[K_BASE_PATH]

        path = folder.lower() if folder[0] == '/' else base_path.lower() + '/' + folder.lower()

        self.folders[path] = {} if description is None else description
        return self

    def add_folders(self, folders):
        for folder, description in folders.items():
            self.add_folder(base_path=None, folder=folder, description=description)

        return self

    def add_full_folder_path(self, path):
        self.folders[path.lower()] = {}
        return self

    def fix_description(self, file, description):
        fixed_description = {
            'hash': description['hash'] if 'hash' in description else Path(file).name,
            'size': description['size'] if 'size' in description else 1
        }

        if 'unzipped_json' in description:
            fixed_description['unzipped_json'] = description['unzipped_json']
        if 'zipped_files' in description:
            fixed_description['zipped_files'] = description['zipped_files']
        if 'content' in description:
            fixed_description['content'] = description['content']

        return fixed_description


def _fs_paths(paths, base_path):
    return {k.lower() if k[0] == '/' else base_path + remove_priority_path(k.lower()): _clean_description(v) for k, v in paths.items()}


def _fs_folders(paths, base_path):
    return {p.lower() if p[0] == '/' else base_path + remove_priority_path(p.lower()): {} for p in paths}


def _fix_base_path(base_path):
    return base_path + '/' if (base_path != '' and base_path[-1] != '/') else base_path


def _fs_system_paths(paths):
    paths = {p: True for p in paths} if isinstance(paths, list) else paths
    if not isinstance(paths, dict):
        raise Exception('system_paths should be a dict.')
    return paths


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
    if 'content' in description:
        result['content'] = description['content']
    return result


class ImporterImplicitInputs:
    def __init__(self, files=None, folders=None, base_path=None, config=None, remote_failures=None, remote_files=None, storing_problems=None, path_dictionary=None):
        self.file_system_state = FileSystemState(
            files=files,
            folders=folders,
            base_path=base_path,
            config=config,
            path_dictionary=path_dictionary
        )

        self.network_state = NetworkState(
            remote_failures=remote_failures,
            remote_files=remote_files,
            storing_problems=storing_problems
        )

    @property
    def config(self):
        return self.file_system_state.config
