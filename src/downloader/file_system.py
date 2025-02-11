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
import sys
import tempfile
import threading
import time
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set, Dict, Any, Tuple, Union

from downloader.config import AllowDelete, Config
from downloader.constants import HASH_file_does_not_exist
from downloader.logger import Logger, PrintLogger
from downloader.other import ClosableValue
from downloader.path_package import PathPackage


is_windows = os.name == 'nt'
COPY_BUFSIZE = 1024 * 1024 if is_windows else 64 * 1024


class FileSystemFactory:
    def __init__(self, config: Config, path_dictionary: Dict[str, str], logger: Logger):
        self._config = config
        self._path_dictionary = path_dictionary
        self._logger = logger
        self._unique_temp_filenames: Set[Optional[str]] = set()
        self._unique_temp_filenames.add(None)
        self._shared_state = FsSharedState()

    def create_for_system_scope(self) -> 'FileSystem':
        return self.create_for_config(self._config)

    def create_for_config(self, config) -> 'FileSystem':
        return _FileSystem(config, self._path_dictionary, self._logger, self._unique_temp_filenames, self._shared_state)

    def cancel_ongoing_operations(self):
        self._shared_state.interrupting_operations = True


class FileSystem(ABC):

    @abstractmethod
    def unique_temp_filename(self, register: bool = True) -> ClosableValue:
        """interface"""

    @abstractmethod
    def persistent_temp_dir(self) -> str:
        """interface"""

    @abstractmethod
    def resolve(self, path: str) -> str:
        """interface"""

    @abstractmethod
    def is_file(self, path: str, use_cache: bool = True) -> bool:
        """interface"""

    @abstractmethod
    def are_files(self, file_pkgs: List[PathPackage]) -> Tuple[List[PathPackage], List[PathPackage]]:
        """interface"""

    @abstractmethod
    def print_debug(self) -> None:
        """interface"""

    @abstractmethod
    def is_folder(self, path: str) -> bool:
        """interface"""

    @abstractmethod
    def precache_is_file_with_folders(self, folders: List[PathPackage], recheck: bool = False) -> None:
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
    def size(self, path: str) -> int:
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
    def write_incoming_stream(self, in_stream: Any, target_path: str, timeout: int):
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
    def unzip_contents(self, file: str, target_path: Union[str, Dict[str, str]], test_info: Any) -> None:
        """interface"""

    @abstractmethod
    def turn_off_logs(self) -> None:
        """interface"""


class ReadOnlyFileSystem:
    def __init__(self, fs: FileSystem):
        self._fs = fs

    def is_file(self, path):
        return self._fs.is_file(path)

    def are_files(self, file_pkgs: List[PathPackage]) -> Tuple[List[PathPackage], List[PathPackage]]:
        return self._fs.are_files(file_pkgs)

    def is_folder(self, path):
        return self._fs.is_folder(path)

    def precache_is_file_with_folders(self, folders: List[PathPackage], recheck: bool = False):
        return self._fs.precache_is_file_with_folders(folders, recheck)

    def download_target_path(self, path):
        return self._fs.download_target_path(path)

    def read_file_contents(self, path):
        return self._fs.read_file_contents(path)

    def load_dict_from_file(self, path, suffix=None):
        return self._fs.load_dict_from_file(path, suffix)

    def folder_has_items(self, path):
        return self._fs.folder_has_items(path)

    def hash(self, path):
        return self._fs.hash(path)

    def size(self, path):
        return self._fs.size(path)

    def unique_temp_filename(self):
        return self._fs.unique_temp_filename()

    def unlink(self, file_path, verbose=False, exception=None):
        if isinstance(exception, UnlinkTemporaryException):
            self._fs.unlink(file_path)
            return

        raise FileWriteError(f"Cannot delete file '{file_path}' from read-only filesystem wrapper")


class UnlinkTemporaryException: pass
class FsError(Exception): pass
class FsOperationsError(FsError): pass
class FolderCreationError(FsError): pass
class FileCopyError(FsError): pass
class UnzipError(FsError): pass
class FileReadError(FsError): pass
class FileWriteError(FsError): pass
class FsTimeoutError(FsError): pass

class _FileSystem(FileSystem):
    def __init__(self, config: Config, path_dictionary: Dict[str, str], logger: Logger, unique_temp_filenames: Set[Optional[str]], shared_state: 'FsSharedState'):
        self._config = config
        self._path_dictionary = path_dictionary
        self._logger = logger
        self._unique_temp_filenames = unique_temp_filenames
        self._shared_state = shared_state
        self._quick_hit = 0
        self._slow_hit = 0

    def unique_temp_filename(self, register: bool = True) -> ClosableValue:
        name = None
        while name in self._unique_temp_filenames:
            name = os.path.join(tempfile._get_default_tempdir(), next(tempfile._get_candidate_names()))
        self._unique_temp_filenames.add(name)
        return ClosableValue(name, lambda: self._unique_temp_filenames.remove(name))

    def persistent_temp_dir(self) -> str:
        return tempfile._get_default_tempdir()

    def resolve(self, path: str) -> str:
        return str(Path(path).resolve())

    def is_file(self, path: str, use_cache: bool = True) -> bool:
        full_path = self._path(path)
        if use_cache and self._shared_state.contains_file(full_path):
            self._quick_hit += 1
            return True
        elif os.path.isfile(full_path):
            self._slow_hit += 1
            self._shared_state.add_file(full_path)
            return True

        return False

    def are_files(self, file_pkgs: List[PathPackage]) -> Tuple[List[PathPackage], List[PathPackage]]:
        are, not_sure = self._shared_state.contained_file_pkgs(file_pkgs)
        bulk_add = []
        nope = []
        for f in not_sure:
            if os.path.isfile(f.full_path):
                bulk_add.append(f.full_path)
                are.append(f)
            else:
                nope.append(f)
        self._shared_state.add_many_files(bulk_add)
        return are, nope

    def print_debug(self) -> None:
        self._logger.debug(f'IS_FILE quick hits: {self._quick_hit} slow hits: {self._slow_hit}')

    def is_folder(self, path: str) -> bool:
        return os.path.isdir(self._path(path))

    def precache_is_file_with_folders(self, folders: List[PathPackage], recheck: bool = False) -> None:
        not_checked_folders = folders if recheck else self._shared_state.consult_not_checked_folders(folders)
        try:
            self._shared_state.add_many_files([f.path for folder_pkg in not_checked_folders for f in os.scandir(folder_pkg.full_path) if f.is_file()])
        except Exception as e:
            self._logger.debug(e)
            for folder_pkg in not_checked_folders:
                try:
                    self._shared_state.add_many_files([f.path for f in os.scandir(folder_pkg.full_path) if f.is_file()])
                except OSError:
                    continue
                except Exception as e:
                    return

    def read_file_contents(self, path: str) -> str:
        full_path = self._path(path)
        self._debug_log('Reading file contents', (path, full_path))
        with open(full_path, 'r') as f:
            return f.read()

    def write_file_contents(self, path: str, content: str) -> int:
        full_path = self._path(path)
        self._debug_log('Writing file contents', (path, full_path))
        with open(full_path, 'w') as f:
            return f.write(content)

    def touch(self, path: str) -> None:
        full_path = self._path(path)
        self._debug_log('Touching', (path, full_path))
        Path(full_path).touch()

    def move(self, source: str, target: str) -> None:
        self._makedirs(self._parent_folder(target))
        full_source = self._path(source)
        full_target = self._path(target)
        self._debug_log('Moving', (source, full_source), (target, full_target))
        os.replace(full_source, full_target)
        self._shared_state.remove_file(full_source)
        self._shared_state.add_file(full_target)

    def copy(self, source: str, target: str) -> None:
        full_source = self._path(source)
        full_target = self._path(target)
        self._debug_log('Copying', (source, full_source), (target, full_target))
        try:
            shutil.copyfile(full_source, full_target, follow_symlinks=True)
        except Exception as e:
            self._logger.debug(e)
            raise FileCopyError(f"Cannot copy '{source}' to '{target}'") from e
        self._shared_state.add_file(full_target)

    def copy_fast(self, source: str, target: str) -> None:
        full_source = self._path(source)
        full_target = self._path(target)
        self._debug_log('Copying', (source, full_source), (target, full_target))
        with open(full_source, 'rb') as fsource:
            with open(full_target, 'wb') as ftarget:
                shutil.copyfileobj(fsource, ftarget, length=1024 * 1024 * 4)
        self._shared_state.add_file(full_target)

    def hash(self, path: str) -> str:
        try:
            return hash_file(self._path(path))
        except Exception as e:
            self._logger.debug(e)
            sys.exit(1)
            return HASH_file_does_not_exist

    def size(self, path: str) -> int:
        try:
            return os.path.getsize(self._path(path))
        except Exception as e:
            self._logger.debug(e)
            return -1

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
        except Exception as e:
            self._logger.debug(e)
            raise FolderCreationError(target) from e

    def folder_has_items(self, path: str) -> bool:
        try:
            iterator = os.scandir(self._path(path))
            for _ in iterator:
                iterator.close()
                return True

        except OSError as e:
            self._ignore_error(e)

        return False

    def folders(self) -> List[str]:
        raise Exception('folders Not implemented')

    def remove_folder(self, path: str) -> None:
        if self._config['allow_delete'] != AllowDelete.ALL:
            return

        full_path = self._path(path)
        self._debug_log('Deleting empty folder', (path, full_path))
        try:
            os.rmdir(full_path)
        except OSError as e:
            self._ignore_error(e)

    def _ignore_error(self, e: Exception) -> None:
        self._logger.debug(e)
        self._logger.debug('Ignoring error.')

    def remove_non_empty_folder(self, path: str) -> None:
        if self._config['allow_delete'] != AllowDelete.ALL:
            return

        full_path = self._path(path)
        self._debug_log('Deleting non-empty folder', (path, full_path))
        try:
            shutil.rmtree(full_path)
        except Exception as e:
            self._ignore_error(e)

    def download_target_path(self, path: str) -> str:
        return self._path(path)

    def write_incoming_stream(self, in_stream: Any, target_path: str, timeout: int):
        start_time = time.time()
        with open(target_path, 'wb') as out_file:
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    raise FsTimeoutError(f"Copy operation timed out after {timeout} seconds.")

                if self._shared_state.interrupting_operations:
                    raise FsOperationsError("File system operations have been disabled.")

                buf = in_stream.read(COPY_BUFSIZE)
                if not buf:
                    break
                out_file.write(buf)

    def unlink(self, path: str, verbose: bool = True) -> bool:
        verbose = verbose and not path.startswith('/tmp/')
        if self._config['allow_delete'] != AllowDelete.ALL:
            if self._config['allow_delete'] == AllowDelete.OLD_RBF and path[-4:].lower() == ".rbf":
                return self._unlink(path, verbose)

            return True

        return self._unlink(path, verbose)

    def load_dict_from_file(self, path: str, suffix: Optional[str] = None) -> Dict[str, Any]:
        full_path = self._path(path)
        self._debug_log('Loading dict from file', (path, full_path))

        if suffix is None:
            suffix = Path(full_path).suffix.lower()
        if suffix == '.json':
            return _load_json(full_path)
        elif suffix == '.zip':
            return load_json_from_zip(full_path)
        else:
            raise FileReadError('File type "%s" not supported' % suffix)

    def save_json_on_zip(self, db: Dict[str, Any], path: str) -> None:
        full_path = self._path(path)
        json_name = Path(path).stem
        zip_path = Path(full_path).absolute()

        self._debug_log('Saving json on zip', (path, full_path))

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr(json_name, json.dumps(db))

    def save_json(self, db: Dict[str, Any], path: str) -> None:
        full_path = self._path(path)
        self._debug_log('Saving json on zip', (path, full_path))
        with open(full_path, 'w') as f:
            json.dump(db, f)

    def unzip_contents(self, zip_file: str, target_path: Union[str, Dict[str, str]], test_info: Any) -> None:
        self._debug_log('Unzipping contents', (zip_file))
        files_to_unzip = None if isinstance(target_path, str) else target_path
        try:
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                if files_to_unzip is None:
                    zipf.extractall(target_path)
                    return

                for member in zipf.infolist():
                    if member.filename not in files_to_unzip:
                        continue

                    if self._shared_state.interrupting_operations:
                        raise FsOperationsError("File system operations have been disabled.")

                    file_path = files_to_unzip[member.filename]
                    with zipf.open(member) as source, open(file_path, 'wb') as target:
                        while True:
                            buf = source.read(COPY_BUFSIZE)
                            if not buf:
                                break
                            target.write(buf)

        except Exception as e:
            self._logger.debug(e)
            raise UnzipError(f"Cannot unzip '{zip_file}' ['{target_path if isinstance(target_path, str) else len(target_path)}']") from e

    def _debug_log(self, message: str, path: Tuple[str, str], target: Optional[Tuple[str, str]] = None) -> None:
        if path[0][0] == '/':
            if target is None:
                self._logger.debug(f'{message} "{path[0]}"')
            else:
                self._logger.debug(f'{message} "{path[0]}" to "{target[0]}"')
        else:
            if target is None:
                self._logger.debug(f'{message} "{path[0]}". {path[1]}')
            else:
                self._logger.debug(f'{message} "{path[0]}" to "{target[0]}". {path[1]} -> {target[1]}')

    def turn_off_logs(self) -> None:
        self._logger = PrintLogger(self._config['start_time'])

    def _unlink(self, path: str, verbose: bool) -> bool:
        full_path = self._path(path)
        if verbose:
            self._logger.print(f'Removing {path} ({full_path})')
        else:
            self._debug_log('Removing', (path, full_path))
        try:
            Path(full_path).unlink()
            self._shared_state.remove_file(full_path)
            return True
        except FileNotFoundError as _:
            return False

    def _path(self, path: str) -> str:
        if path[0] == '/' or os.path.isabs(path):
            return path

        return os.path.join(self._config['base_path'], path)


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
            raise FileReadError('Could not load "%s", because it has %s elements!' % (path, len(namelist)))
        with jsonzipf.open(namelist[0]) as store_json_file:
            return json.loads(store_json_file.read())


def _load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as f:
        return json.loads(f.read())


class FsSharedState:
    def __init__(self) -> None:
        self.interrupting_operations = False
        self._files: Set[str] = set()
        self._files_lock = threading.Lock()
        self._cached_folders = set()
        self._cached_folders_lock = threading.Lock()

    def consult_not_checked_folders(self, folders: List[PathPackage]) -> List[PathPackage]:
        precaching_folders = []
        with self._cached_folders_lock:
            for folder_pkg in folders:
                if folder_pkg.full_path not in self._cached_folders:
                    self._cached_folders.add(folder_pkg.full_path)
                    precaching_folders.append(folder_pkg)

        return precaching_folders

    def contains_file(self, path: str) -> bool:
        with self._files_lock:
            return path in self._files

    def contained_file_pkgs(self, pkgs: List[PathPackage]) -> Tuple[List[PathPackage], List[PathPackage]]:
        if len(pkgs) == 0: return [], []
        contained = []
        foreigns = []
        with self._files_lock:
            for p in pkgs:
                if p.full_path in self._files:
                    contained.append(p)
                else:
                    foreigns.append(p)
        return contained, foreigns

    def add_many_files(self, paths: List[str]) -> None:
        if len(paths) == 0: return
        with self._files_lock:
            self._files.update(paths)

    def add_file(self, path: str) -> None:
        with self._files_lock:
            self._files.add(path)

    def remove_file(self, path: str) -> None:
        with self._files_lock:
            if path in self._files: self._files.remove(path)
