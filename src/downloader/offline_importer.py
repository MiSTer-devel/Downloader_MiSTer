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
    def __init__(self, config, file_service, downloader_factory, logger):
        self._config = config
        self._file_service = file_service
        self._downloader_factory = downloader_factory
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

        self._logger.print()
        db = self._file_service.load_db_from_file(db_file)

        if store_id != db['db_id']:
            self._logger.print('WARNING! Stored id "%s", doesn\'t match Offline database id "%s" at %s' % (
                store_id, db['db_id'], db_file))
            self._logger.print('Ignoring the offline database.')
            return

        self._logger.print('Importing %s into the local store.' % db_file)

        if isinstance(db['folders'], list): # TODO Remove conversion
            db['folders'] = {folder: {} for folder in db['folders']}

        self._import_folders(db['folders'], store['folders'])
        self._import_files(db['files'], store['files'])

        errors = []
        if len(db['zips']) > 0:
            errors.extend(self._update_from_zips(db, store))

        if len(db['files']) > 0:
            self._logger.print()
        self._logger.print()

        if len(errors) == 0:
            store['offline_databases_imported'].append(hash_db_file)
            self._remove_db_file(db_file)
        else:
            for e in errors:
                self._logger.print('Offline importer error: ' + e)
            self._logger.print()

    def _update_from_zips(self, db, store):
        summary_downloader = self._downloader_factory(self._config)
        zip_ids_by_temp_zip = dict()

        for zip_id in db['zips']:
            temp_zip = '/tmp/%s.json.zip' % zip_id
            zip_ids_by_temp_zip[temp_zip] = zip_id

            summary_downloader.queue_file(db['zips'][zip_id]['summary_file'], temp_zip)

        self._logger.print()
        self._logger.print()
        summary_downloader.download_files(False)
        self._logger.print()

        for temp_zip in summary_downloader.correctly_downloaded_files():
            summary = self._file_service.load_db_from_file(temp_zip)
            if isinstance(summary['folders'], list): # TODO Remove conversion
                summary['folders'] = {folder: {} for folder in summary['folders']}

            zip_id = zip_ids_by_temp_zip[temp_zip]

            store['zips'][zip_id] = db['zips'][zip_id]
            store['zips'][zip_id]['folders'] = {}
            self._import_folders(summary['folders'], store['zips'][zip_id]['folders'])
            self._import_files(summary['files'], store['files'])
            self._file_service.unlink(temp_zip)

        return summary_downloader.errors()

    def _import_files(self, files, store_files):
        for file_path, file_description in files.items():
            if self._file_service.is_file(file_path) and \
                    (file_description['hash'] == 'ignore' or self._file_service.hash(file_path) == file_description['hash']) and \
                    file_path not in store_files:
                store_files[file_path] = file_description

                self._logger.print('+', end='', flush=True)

    def _import_folders(self, db_folders, store_folders):
        for folder_path, folder_description in db_folders.items():
            if self._file_service.is_folder(folder_path) and folder_path not in store_folders:
                store_folders[folder_path] = folder_description

    def _remove_db_file(self, db_file):
        if self._config['allow_delete'] == AllowDelete.ALL:
            self._file_service.unlink(db_file)
