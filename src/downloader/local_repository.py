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
import os
from typing import Optional, Any

from downloader.constants import FILE_downloader_storage_zip, FILE_downloader_log, \
    FILE_downloader_last_successful_run, FILE_downloader_external_storage, FILE_downloader_storage_json, \
    FILE_downloader_storage_sigs_json, FILE_downloader_previous_free_space_json
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.fail_policy import FailPolicy
from downloader.file_system import FileSystem, FsError
from downloader.local_store_wrapper import LocalStoreWrapper, DbStateSig
from downloader.logger import FilelogSaver, Logger
from downloader.other import empty_store_without_base_path
from downloader.store_migrator import make_new_local_store, StoreMigrator
from downloader.config import Config


class LocalRepository(FilelogSaver):
    def __init__(self, config: Config, logger: Logger, file_system: FileSystem, store_migrator: StoreMigrator, external_drives_repository: ExternalDrivesRepository, fail_policy: FailPolicy = FailPolicy.FAULT_TOLERANT) -> None:
        self._config = config
        self._logger = logger
        self._file_system = file_system
        self._store_migrator = store_migrator
        self._external_drives_repository = external_drives_repository
        self._fail_policy = fail_policy
        self._storage_path_save_value: Optional[str] = None
        self._storage_path_old_value: Optional[str] = None
        self._storage_path_load_value: Optional[str] = None
        self._store_sigs_path_value: Optional[str] = None
        self._previous_free_spaces_path_value: Optional[str] = None
        self._last_successful_run_value: Optional[str] = None
        self._logfile_path_value: Optional[str] = None

    @property
    def _storage_save_path(self) -> str:
        if self._storage_path_save_value is None:
            self._storage_path_save_value = os.path.join(self._config['base_system_path'], FILE_downloader_storage_json)
        return self._storage_path_save_value

    @property
    def _storage_old_path(self) -> str:
        if self._storage_path_old_value is None:
            self._storage_path_old_value = os.path.join(self._config['base_system_path'], FILE_downloader_storage_zip)
        return self._storage_path_old_value

    @property
    def _storage_load_path(self) -> str:
        if self._storage_path_load_value is None:
            if self._file_system.is_file(self._storage_old_path):
                store_path = self._storage_old_path
            else:
                store_path = self._storage_save_path
            self._storage_path_load_value = store_path
        return self._storage_path_load_value

    @property
    def _store_sigs_path(self) -> str:
        if self._store_sigs_path_value is None:
            self._store_sigs_path_value = os.path.join(self._config['base_system_path'], FILE_downloader_storage_sigs_json)
        return self._store_sigs_path_value

    @property
    def _previous_free_spaces_path(self) -> str:
        if self._previous_free_spaces_path_value is None:
            self._previous_free_spaces_path_value = os.path.join(self._config['base_system_path'], FILE_downloader_previous_free_space_json)
        return self._previous_free_spaces_path_value

    @property
    def _last_successful_run(self) -> str:
        if self._last_successful_run_value is None:
            self._last_successful_run_value = os.path.join(self._config['base_system_path'], FILE_downloader_last_successful_run % self._config['config_path'].stem)
        return self._last_successful_run_value

    @property
    def logfile_path(self) -> str:
        if self._logfile_path_value is None:
            if self._config['logfile'] is not None:
                self._logfile_path_value = self._config['logfile']
            else:
                self._logfile_path_value = os.path.join(self._config['base_system_path'], FILE_downloader_log % self._config['config_path'].stem)
        return self._logfile_path_value

    def set_logfile_path(self, value) -> None:
        self._logfile_path_value = value

    def ensure_base_paths(self) -> None:
        if not self._file_system.is_folder(self._config['base_path']):
            self._logger.print(f'WARNING! Base path "{self._config["base_path"]}" does not exist. Creating it...')
            self._file_system.make_dirs(self._config['base_path'])
        if not self._file_system.is_folder(self._config['base_system_path']):
            self._logger.print(f'WARNING! Base system path "{self._config["base_system_path"]}" does not exist. Creating it...')
            self._file_system.make_dirs(self._config['base_system_path'])

    def load_store(self):
        self._logger.bench('LocalRepository Load store start.')
        try:
            if self._file_system.is_file(self._storage_load_path):
                local_store = self._file_system.load_dict_from_file(self._storage_load_path)
                self._store_migrator.migrate(local_store)
            else:
                local_store = make_new_local_store(self._store_migrator)

            external_drives = self._store_drives()

            for drive in external_drives:
                external_store_file = os.path.join(drive, FILE_downloader_external_storage)
                if not self._file_system.is_file(external_store_file):
                    continue

                try:
                    self._logger.bench('LocalRepository Open json start.')
                    external_store = self._file_system.load_dict_from_file(external_store_file)
                    self._logger.bench('LocalRepository Open json done.')
                    self._store_migrator.migrate(external_store)  # not very strict with exceptions, because this file is easier to tweak
                except Exception as e:
                    self._logger.debug(e)
                    self._logger.print('Could not load external store for drive "%s"' % drive)
                    continue

                for db_id, external in external_store['dbs'].items():
                    if db_id not in local_store['dbs'] or len(local_store['dbs'][db_id]) == 0:
                        local_store['dbs'][db_id] = empty_store_without_base_path()
                    local_store['dbs'][db_id]['external'] = local_store['dbs'][db_id].get('external', {})
                    local_store['dbs'][db_id]['external'][drive] = external

            return LocalStoreWrapper(local_store)

        except Exception as e:
            if self._fail_policy == FailPolicy.FAIL_FAST:
                raise e
            self._logger.debug(e)
            self._logger.print('ERROR: Could not load store')
            return LocalStoreWrapper(make_new_local_store(self._store_migrator))
        finally:
            self._logger.bench('LocalRepository Load store done.')

    def load_store_sigs(self) -> Optional[dict[str, DbStateSig]]:
        self._logger.bench('LocalRepository Load store sigs start.')
        try:
            if self._file_system.is_file(self._store_sigs_path):
                return self._file_system.load_dict_from_file(self._store_sigs_path)
            else:
                return None
        except Exception as e:
            if self._fail_policy == FailPolicy.FAIL_FAST:
                raise e
            self._logger.debug(e)
            self._logger.print('WARNING: Could not load store sigs')
            return None
        finally:
            self._logger.bench('LocalRepository Load store sigs done.')

    def load_previous_free_spaces(self) -> dict[str, int]:
        self._logger.bench('LocalRepository Load previous free spaces start.')
        try:
            if self._file_system.is_file(self._previous_free_spaces_path):
                return self._file_system.load_dict_from_file(self._previous_free_spaces_path)
            else:
                return {}
        except Exception as e:
            if self._fail_policy == FailPolicy.FAIL_FAST:
                raise e

            self._logger.debug(e)
            self._logger.print('WARNING: Could not load previous free spaces')
            return {}
        finally:
            self._logger.bench('LocalRepository Load previous free spaces done.')

    def save_free_spaces(self, free_spaces: dict[str, int]) -> Optional[Exception]:
        self._logger.bench('LocalRepository Save free spaces start.')
        try:
            self._file_system.make_dirs_parent(self._previous_free_spaces_path)
            self._file_system.save_json(free_spaces, self._previous_free_spaces_path)
        except Exception as e:
            self._logger.debug(e)
            return e

        self._logger.bench('LocalRepository Save free spaces done.')
        return None

    def has_last_successful_run(self):
        return self._file_system.is_file(self._last_successful_run)

    def _store_drives(self):
        return self._external_drives_repository.connected_drives_except_base_path_drives(self._config)

    def save_store(self, local_store_wrapper) -> Optional[Exception]:
        if not local_store_wrapper.needs_save():
            self._logger.debug('Skipping local_store saving...')
            return None

        self._logger.bench('LocalRepository Save store start.')
        local_store = local_store_wrapper.unwrap_local_store()
        external_stores = {}
        for db_id, store in local_store['dbs'].items():
            if 'external' not in store:
                continue

            for drive, external in store['external'].items():
                if drive not in external_stores:
                    external_stores[drive] = make_new_local_store(self._store_migrator)
                    external_stores[drive]['internal'] = False

                external_stores[drive]['dbs'][db_id] = external

            del store['external']

        try:
            self._file_system.make_dirs_parent(self._storage_save_path)
            self._logger.bench('LocalRepository Write store json start.')
            self._file_system.save_json(local_store, self._storage_save_path)
            self._logger.bench('LocalRepository Write store main end.')
            self._file_system.save_json(local_store.get('db_sigs', {}), self._store_sigs_path)
            self._logger.bench('LocalRepository Write store db_sigs end.')
            if self._file_system.is_file(self._storage_old_path) and \
                    self._file_system.is_file(self._storage_save_path, use_cache=False):
                self._file_system.unlink(self._storage_old_path)

            external_drives = set(self._store_drives())

            for drive, store in external_stores.items():
                self._logger.bench('LocalRepository Write external json start: ', drive)
                self._file_system.save_json(store, os.path.join(drive, FILE_downloader_external_storage))
                self._logger.bench('LocalRepository Write external json done: ', drive)
                external_drives.discard(drive)

            for drive in external_drives:
                db_to_clean = os.path.join(drive, FILE_downloader_external_storage)
                if self._file_system.is_file(db_to_clean):
                    self._file_system.unlink(db_to_clean)

            self._file_system.touch(self._last_successful_run)
        except FsError as e:
            self._logger.debug(e)
            return e
        else:
            return None
        finally:
            self._logger.bench('LocalRepository Save store end.')

    def save_log_from_tmp(self, path) -> None:
        try:
            self._file_system.turn_off_logs()
            self._file_system.make_dirs_parent(self.logfile_path)
            self._file_system.copy(path, self.logfile_path)
        except Exception:
            import traceback
            print(f'ERROR: Could not copy log file from "{path}" to "{self.logfile_path}"')
            traceback.print_exc()
