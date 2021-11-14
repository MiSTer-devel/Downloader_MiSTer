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

from .constants import distribution_mister_db_id


class OnlineImporter:    
    def __init__(self, config, file_system, file_downloader_factory, logger):
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._dbs = []
        self._files_that_failed = []
        self._correctly_installed_files = []
        self._processed_files = {}
        self._needs_reboot = False
        self._dbs_folders = None
        self._stores_folders = None

    def add_db(self, db, store):
        self._dbs.append((db, store))

    def download_dbs_contents(self, full_resync):
        self._dbs_folders = set()
        self._stores_folders = set()
        for db, store in self._dbs:
            self._process_db_contents(db, store, full_resync)

        deleted_folder = False

        for folder in sorted(self._stores_folders, key=len, reverse=True):
            if folder in self._dbs_folders:
                continue

            if not self._file_system.is_folder(folder):
                continue

            if self._file_system.folder_has_items(folder):
                continue

            if not deleted_folder:
                deleted_folder = True
                self._logger.print()

            self._file_system.remove_folder(folder)

    def _process_db_contents(self, db, store, full_resync):
        self._print_db_header(db)

        self._import_zip_summaries(db, store)

        self._create_folders(db, store)

        self._remove_missing_files(store['files'], db.files)

        file_downloader = self._file_downloader_factory.create(self._config['parallel_update'])
        file_downloader.set_base_files_url(db.base_files_url)
        needed_zips = dict()

        for file_path in db.files:
            self._assert_valid_path(file_path, db.db_id)

            if file_path in self._processed_files:
                self._logger.print('DUPLICATED: %s' % file_path)
                self._logger.print('Already been processed by database: %s' % self._processed_files[file_path])
                continue

            file_description = db.files[file_path]

            if not full_resync and file_path in store['files'] and \
                    store['files'][file_path]['hash'] == file_description['hash'] and \
                    self._should_not_download_again(file_path):

                continue

            if 'overwrite' in file_description and not file_description['overwrite'] and self._file_system.is_file(file_path):
                if self._file_system.hash(file_path) != file_description['hash']:
                    self._logger.print('%s is already present, and is marked to not be overwritten.' % file_path)
                    self._logger.print('Delete the file first if you wish to update it.')
                continue

            self._processed_files[file_path] = db.db_id

            if 'zip_id' in file_description:
                zip_id = file_description['zip_id']
                if zip_id not in needed_zips:
                     needed_zips[zip_id] = dict()
                needed_zips[zip_id][file_path] = file_description
    
            file_downloader.queue_file(file_description, file_path)

        if len(needed_zips) > 0:
            self._import_zip_contents(db, store, needed_zips, file_downloader)

        file_downloader.download_files(self._is_first_run(store))

        for file_path in file_downloader.errors():
            if file_path in store['files']:
                store['files'].pop(file_path)

        self._files_that_failed.extend(file_downloader.errors())

        for path in file_downloader.correctly_downloaded_files():
            store['files'][path] = db.files[path]

        self._correctly_installed_files.extend(file_downloader.correctly_downloaded_files())

        self._needs_reboot = self._needs_reboot or file_downloader.needs_reboot()

    def _assert_valid_path(self, path, db_id):
        if not isinstance(path, str):
            raise InvalidDownloaderPath("Path is not a string '%s', contact with the author of the database." % str(path))

        if path == '' or path[0] == '/' or path[0] == '.' or path[0] == '\\':
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

        lower_path = path.lower()

        if lower_path in invalid_paths():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)
        
        if db_id != distribution_mister_db_id and lower_path in no_distribution_mister_invalid_paths():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

        parts = lower_path.split('/')
        if '..' in parts or len(parts) == 0 or parts[0] in invalid_folders():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

    def _is_first_run(self, store):
        return len(store['files']) == 0

    def _import_zip_summaries(self, db, store):
        for zip_id in list(store['zips']):
            if zip_id not in db.zips:
                store['zips'].pop(zip_id)

        zip_ids_from_store = []
        zip_ids_to_download = []

        for zip_id in db.zips:
            if zip_id in store['zips'] and store['zips'][zip_id]['summary_file']['hash'] == db.zips[zip_id]['summary_file']['hash']:
                zip_ids_from_store.append(zip_id)
            else:
                zip_ids_to_download.append(zip_id)

        if len(zip_ids_from_store) > 0:
            db.files.update({path: fd for path, fd in store['files'].items() if 'zip_id' in fd and fd['zip_id'] in zip_ids_from_store})
            db.folders.update({path: fd for path, fd in store['folders'].items() if 'zip_id' in fd and fd['zip_id'] in zip_ids_from_store})

        if len(zip_ids_to_download) > 0:
            summary_downloader = self._file_downloader_factory.create(self._config['parallel_update'])
            zip_ids_by_temp_zip = dict()

            for zip_id in zip_ids_to_download:
                temp_zip = '/tmp/%s.json.zip' % zip_id
                zip_ids_by_temp_zip[temp_zip] = zip_id

                summary_downloader.queue_file(db.zips[zip_id]['summary_file'], temp_zip)

            summary_downloader.download_files(self._is_first_run(store))
            self._logger.print()

            for temp_zip in summary_downloader.correctly_downloaded_files():
                summary = self._file_system.load_dict_from_file(temp_zip)
                for file_path, file_description in summary['files'].items():
                    db.files[file_path] = file_description
                    if file_path in store['files']:
                        store['files'][file_path] = file_description
                db.folders.update(summary['folders'])
                self._file_system.unlink(temp_zip)

            for temp_zip in summary_downloader.errors():
                zip_id = zip_ids_by_temp_zip[temp_zip]
                if zip_id in store['zips']:
                    db.folders.update(store['zips'][zip_id]['folders'])
                    db.files.update({path: fd for path, fd in store['files'].items() if 'zip_id' in fd and fd['zip_id'] in zip_ids_from_store})

            self._files_that_failed.extend(summary_downloader.errors())

    def _import_zip_contents(self, db, store, needed_zips, file_downloader):
        zip_downloader = self._file_downloader_factory.create(self._config['parallel_update'])
        zip_ids_by_temp_zip = dict()
        for zip_id in needed_zips:
            zipped_files = needed_zips[zip_id]
            if len(zipped_files) < self._config['zip_file_count_threshold']:
                for file_path in zipped_files:
                    file_downloader.queue_file(zipped_files[file_path], file_path)
                store['zips'][zip_id] = db.zips[zip_id]
            else:
                temp_zip = '/tmp/%s_contents.zip' % zip_id
                zip_ids_by_temp_zip[temp_zip] = zip_id
                zip_downloader.queue_file(db.zips[zip_id]['contents_file'], temp_zip)

        if len(zip_ids_by_temp_zip) > 0:
            zip_downloader.download_files(self._is_first_run(store))
            self._logger.print()
            for temp_zip in sorted(zip_downloader.correctly_downloaded_files()):
                zip_id = zip_ids_by_temp_zip[temp_zip]
                path = db.zips[zip_id]['path']
                contents = ', '.join(db.zips[zip_id]['contents'])
                self._logger.print('Unpacking %s at %s' % (contents, 'the root' if path == './' else path))
                self._file_system.unzip_contents(temp_zip, db.zips[zip_id]['path'])
                self._file_system.unlink(temp_zip)
                file_downloader.mark_unpacked_zip(zip_id, db.zips[zip_id]['base_files_url'])
                store['zips'][zip_id] = db.zips[zip_id]
            self._logger.print()
            self._files_that_failed.extend(zip_downloader.errors())

    def _print_db_header(self, db):
        self._logger.print()
        if db.header is not None:
            self._logger.print('################################################################################')
            for line in db.header:
                self._logger.print(line, end='')
        else:
            self._logger.print('################################################################################')
            self._logger.print('SECTION: %s' % db.db_id)
            self._logger.print()

    def _should_not_download_again(self, file_path):
        if not self._config['check_manually_deleted_files']:
            return True

        return self._file_system.is_file(file_path)

    def _create_folders(self, db, store):
        for folder in db.folders:
            self._assert_valid_path(folder, db.db_id)
            self._file_system.makedirs(folder)

        self._dbs_folders |= set(db.folders)
        self._stores_folders |= set(store['folders'])

        store['folders'] = db.folders

    def _remove_missing_files(self, store_files, db_files):
        files_to_delete = [f for f in store_files if f not in db_files]

        for file_path in files_to_delete:
            self._file_system.unlink(file_path)
            if file_path in store_files:
                store_files.pop(file_path)

        if len(files_to_delete) > 0:
            self._logger.print()

    def files_that_failed(self):
        return self._files_that_failed

    def correctly_installed_files(self):
        return self._correctly_installed_files

    def needs_reboot(self):
        return self._needs_reboot


class InvalidDownloaderPath(Exception):
    pass


def no_distribution_mister_invalid_paths():
    return ('mister', 'menu.rbf')


def invalid_paths():
    return ('mister.ini', 'mister_alt.ini', 'mister_alt_1.ini', 'mister_alt_2.ini', 'mister_alt_3.ini', 'scripts/downloader.sh', 'mister.new')


def invalid_folders():
    return ('linux', 'saves', 'savestates', 'screenshots')
