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
from .constants import file_MiSTer_old, file_downloader_storage, file_downloader_log, file_downloader_last_successful_run
from .store_migrator import make_new_local_store


class LocalRepository:
    def __init__(self, config, logger, file_system):
        self._config = config
        self._logger = logger
        self._file_system = file_system
        self._storage_path_value = None
        self._last_successful_run_value = None
        self._logfile_path_value = None
        self._old_mister_path = None

    @property
    def _storage_path(self):
        if self._storage_path_value is None:
            self._storage_path_value = file_downloader_storage
            self._file_system.add_system_path(self._storage_path_value)
        return self._storage_path_value

    @property
    def _last_successful_run(self):
        if self._last_successful_run_value is None:
            self._last_successful_run_value = file_downloader_last_successful_run % self._config[
                'config_path'].stem
            self._file_system.add_system_path(self._last_successful_run_value)
        return self._last_successful_run_value

    @property
    def logfile_path(self):
        if self._logfile_path_value is None:
            self._logfile_path_value = file_downloader_log % self._config['config_path'].stem
            self._file_system.add_system_path(self._logfile_path_value)
        return self._logfile_path_value

    @property
    def old_mister_path(self):
        if self._old_mister_path is None:
            self._old_mister_path = file_MiSTer_old
            self._file_system.add_system_path(self._old_mister_path)
        return self._old_mister_path

    def load_store(self, store_migrator):
        if not self._file_system.is_file(self._storage_path):
            return make_new_local_store(store_migrator)

        try:
            local_store = self._file_system.load_dict_from_file(self._storage_path)
        except Exception as e:
            self._logger.debug(e)
            self._logger.print('Could not load storage')
            return make_new_local_store(store_migrator)

        store_migrator.migrate(local_store)
        return local_store

    def has_last_successful_run(self):
        return self._file_system.is_file(self._last_successful_run)

    def save_store(self, local_store):
        self._file_system.make_dirs_parent(self._storage_path)
        self._file_system.save_json_on_zip(local_store, self._storage_path)
        self._file_system.touch(self._last_successful_run)

    def save_log_from_tmp(self, path):
        self._file_system.copy(path, self.logfile_path)

