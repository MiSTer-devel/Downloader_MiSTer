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

class OnlineImporter:
    def __init__(self, config, file_service, downloader_factory, logger):
        self._config = config
        self._file_service = file_service
        self._downloader_factory = downloader_factory
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

        for folder in sorted(self._stores_folders, key=len, reverse=True):
            if folder in self._dbs_folders:
                continue

            if self._file_service.folder_has_items(folder):
                continue

            self._file_service.remove_folder(folder)

    def _process_db_contents(self, db, store, full_resync):
        self._print_db_header(db)

        self._create_folders(db, store)

        first_run = len(store['files']) == 0
        self._remove_missing_files(store['files'], db['files'])

        downloader = self._downloader_factory(self._config)

        for file_path in db['files']:
            if not full_resync and file_path in store['files'] and \
                    store['files'][file_path]['hash'] == db['files'][file_path]['hash'] and \
                    self._should_not_download_again(file_path):
                continue

            if file_path in self._processed_files:
                self._logger.print('DUPLICATED: %s' % file_path)
                self._logger.print('Already been processed by database: %s' % self._processed_files[file_path])
                continue

            file_description = db['files'][file_path]
            if 'overwrite' in file_description and not file_description['overwrite'] and self._file_service.is_file(file_path):
                self._logger.print('%s is already present, and is marked to not be overwritten.' % file_path)
                self._logger.print('Delete the file first if you wish to update it.')
                continue

            downloader.queue_file(file_description, file_path)
            self._processed_files[file_path] = db['db_id']

        downloader.download_files(first_run)

        for file_path in downloader.errors():
            if file_path in store['files']:
                store['files'].pop(file_path)

        self._files_that_failed.extend(downloader.errors())

        for path in downloader.correctly_downloaded_files():
            store['files'][path] = db['files'][path]

        self._correctly_installed_files.extend(downloader.correctly_downloaded_files())

        self._needs_reboot = self._needs_reboot or downloader.needs_reboot()

    def _print_db_header(self, db):
        if 'header' in db:
            for line in db['header']:
                self._logger.print(line, end='')
        else:
            self._logger.print()
            self._logger.print('################################################################################')
            self._logger.print('SECTION: %s' % db['db_id'])
            self._logger.print('################################################################################')
            self._logger.print()

    def _should_not_download_again(self, file_path):
        if not self._config['check_manually_deleted_files']:
            return True

        return self._file_service.is_file(file_path)

    def _create_folders(self, db, store):
        for folder in db['folders']:
            self._file_service.makedirs(folder)

        self._dbs_folders = self._dbs_folders | set(db['folders'])
        self._stores_folders = self._stores_folders | set(store['folders'])
        store['folders'] = db['folders']

    def _remove_missing_files(self, store_files, db_files):
        files_to_delete = [f for f in store_files if f not in db_files]

        for file_path in files_to_delete:
            self._file_service.unlink(file_path)
            store_files.pop(file_path)

        if len(files_to_delete) > 0:
            self._logger.print()

    def files_that_failed(self):
        return self._files_that_failed

    def correctly_installed_files(self):
        return self._correctly_installed_files

    def needs_reboot(self):
        return self._needs_reboot
