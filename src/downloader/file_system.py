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

import os
import hashlib
import shutil
import json
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set, Dict, Any

from downloader.config import AllowDelete
from downloader.constants import K_ALLOW_DELETE, K_BASE_PATH
from downloader.logger import Logger
from downloader.other import ClosableValue
import zipfile


is_windows = os.name == 'nt'


class FileSystemFactory:
    def __init__(self, config: Dict[str, Any], path_dictionary: Dict[str, str], logger: Logger):
        self._config = config
        self._path_dictionary = path_dictionary
        self._logger = logger
        self._unique_temp_filenames: Set[Optional[str]] = set()
        self._unique_temp_filenames.add(None)
        self._fs_cache = FsCache()

    def create_for_system_scope(self) -> 'FileSystem':
        return self.create_for_config(self._config)

    def create_for_config(self, config) -> 'FileSystem':
        return _FileSystem(config, self._path_dictionary, self._logger, self._unique_temp_filenames, self._fs_cache)


class FileSystem(ABC):

    @abstractmethod
    def unique_temp_filename(self) -> ClosableValue:
        """interface"""

    @abstractmethod
    def resolve(self, path: str) -> str:
        """interface"""

    @abstractmethod
    def is_file(self, path: str) -> bool:
        """interface"""

    @abstractmethod
    def print_debug(self) -> None:
        """interface"""

    @abstractmethod
    def is_folder(self, path: str) -> bool:
        """interface"""

    @abstractmethod
    def precache_is_file_with_folders(self, folders: List[str]) -> None:
        """interface"""

    @abstractmethod
    def read_file_contents(self, path: str) -> str:
        """interface"""

    @abstractmethod
    def write_file_contents(self, path: str, content: str) -> int:
        """interface"""

    @abstractmethod
    def touch(self, path: str) -> None:
        """interface"""

    @abstractmethod
    def move(self, source: str, target: str) -> None:
        """interface"""

    @abstractmethod
    def copy(self, source: str, target: str) -> None:
        """interface"""

    @abstractmethod
    def copy_fast(self, source: str, target: str) -> None:
        """interface"""

    @abstractmethod
    def hash(self, path: str) -> str:
        """interface"""

    @abstractmethod
    def make_dirs(self, path: str) -> None:
        """interface"""

    @abstractmethod
    def make_dirs_parent(self, path: str) -> None:
        """interface"""

    @abstractmethod
    def folder_has_items(self, path: str) -> bool:
        """interface"""

    @abstractmethod
    def folders(self) -> List[str]:
        """interface"""

    @abstractmethod
    def remove_folder(self, path: str) -> None:
        """interface"""

    @abstractmethod
    def remove_non_empty_folder(self, path: str) -> None:
        """interface"""

    @abstractmethod
    def download_target_path(self, path: str) -> str:
        """interface"""

    @abstractmethod
    def unlink(self, path: str, verbose: bool = True) -> bool:
        """interface"""

    @abstractmethod
    def load_dict_from_file(self, path: str, suffix: Optional[str] = None) -> Dict[str, Any]:
        """interface"""

    @abstractmethod
    def save_json_on_zip(self, db: Dict[str, Any], path: str) -> None:
        """interface"""

    @abstractmethod
    def save_json(self, db: Dict[str, Any], path: str) -> None:
        """interface"""

    @abstractmethod
    def unzip_contents(self, file: str, path: str, contained_files: Any) -> None:
        """interface"""


class FolderCreationError(Exception):
    pass


class _FileSystem(FileSystem):
    def __init__(self, config: Dict[str, Any], path_dictionary: Dict[str, str], logger: Logger, unique_temp_filenames: Set[Optional[str]], fs_cache: 'FsCache'):
        self._config = config
        self._path_dictionary = path_dictionary
        self._logger = logger
        self._unique_temp_filenames = unique_temp_filenames
        self._fs_cache = fs_cache
        self._quick_hit = 0
        self._slow_hit = 0

    def unique_temp_filename(self) -> ClosableValue:
        name = None
        while name in self._unique_temp_filenames:
            name = os.path.join(tempfile._get_default_tempdir(), next(tempfile._get_candidate_names()))
        self._unique_temp_filenames.add(name)
        return ClosableValue(name, lambda: self._unique_temp_filenames.remove(name))

    def resolve(self, path: str) -> str:
        return str(Path(path).resolve())

    def is_file(self, path: str) -> bool:
        full_path = self._path(path)
        if self._fs_cache.contains_file(full_path):
            self._quick_hit += 1
            return True
        elif os.path.isfile(full_path):
            self._slow_hit += 1
            self._fs_cache.add_file(full_path)
            return True

        return False

    def print_debug(self) -> None:
        self._logger.debug(f'IS_FILE quick hits: {self._quick_hit} slow hits: {self._slow_hit}')

    def is_folder(self, path: str) -> bool:
        return os.path.isdir(self._path(path))

    def precache_is_file_with_folders(self, folders: List[str]) -> None:
        for folder_path in folders:
            base_path = self._base_path(folder_path)
            full_folder_path = folder_path if base_path is None else os.path.join(base_path, folder_path)
            if not os.path.isdir(full_folder_path):
                continue

            files = [f.path for f in os.scandir(full_folder_path) if f.is_file()]
            self._fs_cache.add_many_files(files)

    def read_file_contents(self, path: str) -> str:
        with open(self._path(path), 'r') as f:
            return f.read()

    def write_file_contents(self, path: str, content: str) -> int:
        with open(self._path(path), 'w') as f:
            return f.write(content)

    def touch(self, path: str) -> None:
        Path(self._path(path)).touch()

    def move(self, source: str, target: str) -> None:
        self._makedirs(self._parent_folder(target))
        full_source = self._path(source)
        full_target = self._path(target)
        self._logger.debug(f'Moving "{source}" to "{target}". {full_source} -> {full_target}')
        self._logger.debug(self._path_dictionary)
        os.replace(full_source, full_target)
        self._fs_cache.remove_file(full_source)
        self._fs_cache.add_file(full_target)

    def copy(self, source: str, target: str) -> None:
        full_source = self._path(source)
        full_target = self._path(target)
        shutil.copyfile(full_source, full_target)
        self._fs_cache.add_file(full_target)

    def copy_fast(self, source: str, target: str) -> None:
        full_source = self._path(source)
        full_target = self._path(target)
        with open(full_source, 'rb') as fsource:
            with open(full_target, 'wb') as ftarget:
                shutil.copyfileobj(fsource, ftarget, length=1024 * 1024 * 4)
        self._fs_cache.add_file(full_target)

    def hash(self, path: str) -> str:
        return hash_file(self._path(path))

    def make_dirs(self, path: str) -> None:
        self._makedirs(self._path(path))

    def make_dirs_parent(self, path: str) -> None:
        self._makedirs(self._parent_folder(path))

    def _parent_folder(self, path: str) -> str:
        result = absolute_parent_folder(self._path(path))
        if is_windows:
            result = self._path(result)
        return result

    def _makedirs(self, target: str) -> None:
        try:
            os.makedirs(target, exist_ok=True)
        except FileExistsError as e:
            if e.errno == 17:
                return
            raise e
        except FileNotFoundError as e:
            self._logger.debug(e)
            raise FolderCreationError(target)

    def folder_has_items(self, path: str) -> bool:
        try:
            iterator = os.scandir(self._path(path))
            for _ in iterator:
                iterator.close()
                return True

        except FileNotFoundError as e:
            self._ignore_error(e)
        except NotADirectoryError as e:
            self._ignore_error(e)

        return False

    def folders(self) -> List[str]:
        raise Exception('folders Not implemented')

    def remove_folder(self, path: str) -> None:
        if self._config[K_ALLOW_DELETE] != AllowDelete.ALL:
            return

        self._logger.print('Deleting empty folder %s' % path)
        try:
            os.rmdir(self._path(path))
        except FileNotFoundError as e:
            self._ignore_error(e)
        except NotADirectoryError as e:
            self._ignore_error(e)

    def _ignore_error(self, e: Exception) -> None:
        self._logger.debug(e)
        self._logger.debug('Ignoring error.')

    def remove_non_empty_folder(self, path: str) -> None:
        if self._config[K_ALLOW_DELETE] != AllowDelete.ALL:
            return

        try:
            shutil.rmtree(self._path(path))
        except Exception as e:
            self._logger.debug(e)
            self._logger.debug('Ignoring error.')

    def download_target_path(self, path: str) -> str:
        return self._path(path)

    def unlink(self, path: str, verbose: bool = True) -> bool:
        verbose = verbose and not path.startswith('/tmp/')
        if self._config[K_ALLOW_DELETE] != AllowDelete.ALL:
            if self._config[K_ALLOW_DELETE] == AllowDelete.OLD_RBF and path[-4:].lower() == ".rbf":
                return self._unlink(path, verbose)

            return True

        return self._unlink(path, verbose)

    def load_dict_from_file(self, path: str, suffix: Optional[str] = None) -> Dict[str, Any]:
        path = self._path(path)
        if suffix is None:
            suffix = Path(path).suffix.lower()
        if suffix == '.json':
            return _load_json(path)
        elif suffix == '.zip':
            return load_json_from_zip(path)
        else:
            raise Exception('File type "%s" not supported' % suffix)

    def save_json_on_zip(self, db: Dict[str, Any], path: str) -> None:
        json_name = Path(path).stem
        zip_path = Path(self._path(path)).absolute()

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr(json_name, json.dumps(db))

    def save_json(self, db: Dict[str, Any], path: str) -> None:
        with open(self._path(path), 'w') as f:
            json.dump(db, f)

    def unzip_contents(self, file: str, path: str, contained_files: Any) -> None:
        with zipfile.ZipFile(self._path(file), 'r') as zipf:
            zipf.extractall(self._path(path))

        self._unlink(file, False)

    def _unlink(self, path: str, verbose: bool) -> bool:
        full_path = self._path(path)
        if verbose:
            self._logger.print(f'Removing {path} ({full_path})')
        try:
            Path(full_path).unlink()
            self._fs_cache.remove_file(full_path)
            return True
        except FileNotFoundError as _:
            return False

    def _path(self, path: str) -> str:
        base_path = self._base_path(path)
        if base_path is None:
            return path
        else:
            return os.path.join(base_path, path)

    def _base_path(self, path: str) -> Optional[str]:
        if path[0] == '/':
            return None

        if is_windows and len(path) > 2 and path[1:2] == ':\\':
            return None

        path_lower = path.lower()

        if path_lower in self._path_dictionary:
            return self._path_dictionary[path_lower]

        return self._config[K_BASE_PATH]


class InvalidFileResolution(Exception):
    pass


def hash_file(path: str) -> str:
    with open(path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
        return file_hash.hexdigest()


def absolute_parent_folder(absolute_path: str) -> str:
    return str(Path(absolute_path).parent)


def load_json_from_zip(path: str) -> Dict[str, Any]:
    with zipfile.ZipFile(path) as jsonzipf:
        namelist = jsonzipf.namelist()
        if len(namelist) != 1:
            raise Exception('Could not load "%s", because it has %s elements!' % (path, len(namelist)))
        with jsonzipf.open(namelist[0]) as store_json_file:
            return json.loads(store_json_file.read())


def _load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as f:
        return json.loads(f.read())


class FsCache:
    def __init__(self): self._files: Set[str] = set()
    def contains_file(self, path: str) -> bool: return path in self._files

    def add_many_files(self, paths: List[str]) -> None:
        self._files.update(paths)

    def add_file(self, path: str) -> None:
        self._files.add(path)

    def remove_file(self, path: str) -> None:
        if path in self._files: self._files.remove(path)
