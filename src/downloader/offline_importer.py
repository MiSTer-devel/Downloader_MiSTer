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

from downloader.config import AllowDelete
from downloader.constants import K_BASE_PATH, K_ALLOW_DELETE
from downloader.db_entity import DbEntity, DbEntityValidationException


class OfflineImporter:
    def __init__(self, file_system_factory, file_downloader_factory, logger):
        self._file_system_factory = file_system_factory
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger

    def apply_offline_databases(self, importer_command):
        self._logger.bench('Offline Importer start.')

        for db, store, config in importer_command.read_dbs():
            for db_file in db.db_files:
                db_importer = _OfflineDatabaseImporter(config, self._file_system_factory.create_for_config(config), self._file_downloader_factory, self._logger)
                db_importer.update_store_from_offline_db(db.db_id, db_file, store)
                store.write_only().set_base_path(config[K_BASE_PATH])

        self._logger.bench('Offline Importer done.')


class _OfflineDatabaseImporter:
    def __init__(self, config, file_system, file_downloader_factory, logger):
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger

    def update_store_from_offline_db(self, store_id, db_file, store):
        write_store = store.write_only()
        read_store = store.read_only()

        if not self._file_system.is_file(db_file):
            return

        hash_db_file = self._file_system.hash(db_file)
        if hash_db_file in read_store.offline_databases_imported:
            self._remove_db_file(db_file)
            return

        self._logger.print()
        try:
            db = DbEntity(self._file_system.load_dict_from_file(db_file), store_id)
        except DbEntityValidationException as e:
            self._logger.print('WARNING! Offline database "%s", could not be load from file %s' % (store_id, db_file))
            self._logger.debug(e)
            self._logger.print(str(e))
            self._logger.print('Ignoring the offline database.')
            return

        self._logger.print('Importing %s into the local store.' % db_file)

        self._import_folders(db.folders, read_store, write_store)
        self._import_files(db.files, read_store, write_store)

        errors = []
        if len(db.zips) > 0:
            errors.extend(self._update_from_zips(db, read_store, write_store))

        if len(db.files) > 0:
            self._logger.print()
        self._logger.print()

        if len(errors) == 0:
            write_store.add_imported_offline_database(hash_db_file)
            self._remove_db_file(db_file)
        else:
            for e in errors:
                self._logger.print('Offline importer error: ' + e)
            self._logger.print()

    def _update_from_zips(self, db, read_store, write_store):
        summary_downloader = self._file_downloader_factory.create(self._config, parallel_update=True)
        zip_ids_by_temp_zip = dict()

        zip_ids_to_download = []
        zip_ids_from_internal_summary = []

        for zip_id, zip_desc in db.zips.items():
            if 'summary_file' in zip_desc:
                zip_ids_to_download.append(zip_id)
            elif 'internal_summary' in zip_desc:
                zip_ids_from_internal_summary.append(zip_id)

        for zip_id in zip_ids_from_internal_summary:
            summary = db.zips[zip_id]['internal_summary']
            self._import_folders(summary['folders'], read_store, write_store)
            self._import_files(summary['files'], read_store, write_store)
            db.zips[zip_id].pop('internal_summary')
            write_store.add_zip(zip_id, db.zips[zip_id])

        temp_filename = self._file_system.unique_temp_filename()

        for zip_id in zip_ids_to_download:
            temp_zip = '%s_%s.json.zip' % (temp_filename.value, zip_id)
            zip_ids_by_temp_zip[temp_zip] = zip_id

            summary_downloader.queue_file(db.zips[zip_id]['summary_file'], temp_zip)

        temp_filename.close()

        self._logger.print()
        self._logger.print()
        summary_downloader.download_files(False)
        self._logger.print()

        for temp_zip in summary_downloader.correctly_downloaded_files():
            summary = self._file_system.load_dict_from_file(temp_zip)

            zip_id = zip_ids_by_temp_zip[temp_zip]

            if 'summary_file' in db.zips[zip_id] and 'unzipped_json' in db.zips[zip_id]['summary_file']:
                db.zips[zip_id]['summary_file'].pop('unzipped_json')

            write_store.add_zip(zip_id, db.zips[zip_id])
            self._import_folders(summary['folders'], read_store, write_store)
            self._import_files(summary['files'], read_store, write_store)
            self._file_system.unlink(temp_zip)

        return summary_downloader.errors()

    def _import_files(self, files, read_store, write_store):
        for file_path, file_description in files.items():
            if self._file_system.is_file(file_path) and \
                    (file_description['hash'] == 'ignore' or self._file_system.hash(file_path) == file_description['hash']) and \
                    file_path not in read_store.files:
                write_store.add_file(file_path, file_description)

                self._logger.print('+', end='', flush=True)

    def _import_folders(self, db_folders, read_store, write_store):
        for folder_path, folder_description in db_folders.items():
            if self._file_system.is_folder(folder_path) and folder_path not in read_store.folders:
                write_store.add_folder(folder_path, folder_description)

    def _remove_db_file(self, db_file):
        if self._config[K_ALLOW_DELETE] == AllowDelete.ALL:
            self._file_system.unlink(db_file)
