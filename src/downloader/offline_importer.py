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

from .config import AllowDelete


class OfflineImporter:
    def __init__(self, config, file_service, logger):
        self._config = config
        self._file_service = file_service
        self._logger = logger
        self._dbs = []

    def add_db(self, db, store):
        self._dbs.append((db, store))

    def apply_offline_databases(self):
        for db, store in self._dbs:
            for db_file in db['db_files']:
                self._update_store_from_offline_db(db['db_id'], db_file, store)

    def _update_store_from_offline_db(self, store_id, db_file, store):
        if not self._file_service.is_file(db_file):
            return

        hash_db_file = self._file_service.hash(db_file)
        if hash_db_file in store['offline_databases_imported']:
            self._remove_db_file(db_file)
            return

        db = self._file_service.load_db_from_file(db_file)

        if store_id != db['db_id']:
            self._logger.print('WARNING! Stored id "%s", doesn\'t match Offline database id "%s" at %s' % (
                store_id, db['db_id'], db_file))
            self._logger.print('Ignoring the offline database.')
            return

        self._logger.print('Importing %s into the local store.' % db_file)

        for file_path in db['files']:
            if self._file_service.is_file(file_path) and \
                    (db['files'][file_path]['hash'] == 'ignore' or self._file_service.hash(file_path) == db['files'][file_path]['hash']) and \
                    file_path not in store['files']:
                store['files'][file_path] = db['files'][file_path]

                self._logger.print('+', end='', flush=True)

        if len(db['files']) > 0:
            self._logger.print()
        self._logger.print()

        store['offline_databases_imported'].append(hash_db_file)
        self._remove_db_file(db_file)

    def _remove_db_file(self, db_file):
        if self._config['allow_delete'] == AllowDelete.ALL:
            self._file_service.unlink(db_file)
