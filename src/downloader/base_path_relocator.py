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

from typing import Any, Dict, List, Tuple
from downloader.config import Config, config_with_base_path
from downloader.constants import K_BASE_PATH
from downloader.db_utils import DbSectionPackage
from downloader.file_system import FileSystem, FileSystemFactory
from downloader.local_store_wrapper import StoreWrapper
from downloader.logger import Logger
from downloader.waiter import Waiter


class BasePathRelocator:
    def __init__(self, config: Config, file_system_factory: FileSystemFactory, waiter: Waiter, logger: Logger):
        self._config = config
        self._file_system_factory = file_system_factory
        self._waiter = waiter
        self._logger = logger

    def relocating_base_paths(self, db_pkgs: List[DbSectionPackage]) -> List['BasePathRelocatorPackage']:
        result = []
        for pkg in db_pkgs:
            if not pkg.store.read_only().has_base_path():
                pkg.store.write_only().set_base_path(self._config[K_BASE_PATH])

            from_base_path = pkg.store.read_only().base_path
            to_base_path = self._config[K_BASE_PATH]

            if to_base_path == from_base_path:
                self._logger.debug('%s still uses base_path: %s', pkg.db_id, self._config[K_BASE_PATH])
                continue

            from_file_system = self._file_system_factory.create_for_config(config_with_base_path(self._config, from_base_path))
            to_file_system = self._file_system_factory.create_for_config(config_with_base_path(self._config, to_base_path))

            result.append(BasePathRelocatorPackage(
                pkg.store,
                self._config,
                from_file_system,
                to_file_system,
                self._logger,
                self._waiter,
                pkg.db_id
            ))

        return result

    def relocate_non_system_files(self, package: 'BasePathRelocatorPackage') -> None:
        self._logger.bench('Base Path Relocator start: ', package.db_id)

        package.relocate_non_system_files()
        package.update_store()

        self._logger.bench('Base Path Relocator done: ', package.db_id)


class BasePathRelocatorPackage:
    def __init__(self, store: StoreWrapper, config: Config, from_file_system: FileSystem, to_file_system: FileSystem, logger: Logger, waiter: Waiter, db_id: str):
        self._store = store
        self._config = config
        self._from_file_system = from_file_system
        self._to_file_system = to_file_system
        self._logger = logger
        self._waiter = waiter
        self._db_id = db_id

    @property
    def db_id(self): return self._db_id

    def relocate_non_system_files(self) -> None:
        files_to_relocate: Tuple[str, Dict[str, Any]] = []
        for file, description in self._store.read_only().files.items():
            if 'path' in description and description['path'] == 'system':
                continue

            if not self._from_file_system.is_file(file):
                continue

            files_to_relocate.append((file, description))

        if len(files_to_relocate) == 0:
            return

        self._logger.print()
        self._logger.print('Database [%s] changed its base_path!' % self._db_id)
        self._logger.print('Files will be relocated from "%s" to "%s".' % (self._from_base_path, self._to_base_path))
        self._logger.print()
        self._logger.print('DO NOT TURN OFF YOUR MISTER')
        self._waiter.sleep(2)
        self._logger.print()

        old_files = []
        for file, description in files_to_relocate:
            source_path = self._from_file_system.download_target_path(file)
            source_hash = self._from_file_system.hash(file)

            self._logger.print('Relocated: %s ' % file, end='', flush=True)

            self._to_file_system.make_dirs_parent(file)
            self._to_file_system.copy_fast(source_path, file)
            old_files.append(file)

            target_hash = self._to_file_system.hash(file)
            if source_hash != target_hash:
                self._rollback_changes(old_files)
                raise RelocatorError('Relocator failed!')

            self._logger.print('+')

        self._logger.print()
        self._logger.print('Cleaning up old files...')
        for file in old_files:
            self._from_file_system.unlink(file, verbose=False)

        self._logger.print('Cleaning up old folders...')
        folders_to_clean = []

        for folder in self._store.read_only().folders:
            if not self._from_file_system.is_folder(folder):
                continue

            if self._from_file_system.folder_has_items(folder):
                continue

            folders_to_clean.append(folder)

        if len(folders_to_clean) == 0:
            return

        self._logger.print()
        for folder in folders_to_clean:
            self._from_file_system.remove_folder(folder)

    def _rollback_changes(self, old_files) -> None:
        self._logger.print()
        self._logger.print()
        self._logger.print('ERROR: Relocation could not be completed!')
        self._logger.print('The new device failed to receive the files.')
        self._logger.print('Rolling back...')
        self._waiter.sleep(2)

        for file in old_files:
            self._to_file_system.unlink(file, verbose=False)
            self._logger.print('Restored: %s' % file)

    def update_store(self) -> None:
        self._store.write_only().set_base_path(self._to_base_path)

    @property
    def _from_base_path(self) -> str:
        return self._store.read_only().base_path

    @property
    def _to_base_path(self) -> str:
        return self._config[K_BASE_PATH]


class RelocatorError(Exception):
    pass
