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
import time
from downloader.constants import distribution_mister_db_id
from downloader.file_filter import BadFileFilterPartException


class _Session:
    def __init__(self):
        self.files_that_failed = []
        self.correctly_installed_files = []
        self.new_files_not_overwritten = {}
        self.processed_files = {}
        self.needs_reboot = False
        self.dbs_folders = set()
        self.stores_folders = set()
        self.file_system = None

    def add_new_file_not_overwritten(self, db_id, file):
        if db_id not in self.new_files_not_overwritten:
            self.new_files_not_overwritten[db_id] = []
        self.new_files_not_overwritten[db_id].append(file)


class OnlineImporter:
    def __init__(self, file_filter_factory, file_system_factory, file_downloader_factory, logger):
        self._file_filter_factory = file_filter_factory
        self._file_system_factory = file_system_factory
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._unused_filter_tags = []
        self._sessions = dict()
        self._base_session = _Session()

    def download_dbs_contents(self, importer_command, full_resync):

        for session in self._sessions.values():
            session.dbs_folders = set()
            session.stores_folders = set()

        # TODO: Move the filter validation to earlier (before downloading dbs).
        for db, store, config in importer_command.read_dbs():
            self._print_db_header(db)
            file_system = self._file_system_factory.create_for_db_id(db.db_id)
            session = self._session_for_config(config, file_system)

            zip_summaries = _OnlineZipSummaries(db, store, full_resync, config, file_system, self._file_downloader_factory, self._logger, session)
            populated_db = zip_summaries.populate_db_with_summaries()

            file_filter = self._create_file_filter(populated_db, config)
            filtered_db = file_filter.create_filtered_db(populated_db, store)

            db_importer = _OnlineDatabaseImporter(filtered_db, store, full_resync, config, file_system, self._file_downloader_factory, self._logger, session)
            db_importer.process_db_contents()

            store['base_path'] = config['base_path']

        deleted_folder = False

        for session in self._sessions.values():
            for folder in sorted(session.stores_folders, key=len, reverse=True):
                if folder in session.dbs_folders:
                    continue

                if not session.file_system.is_folder(folder):
                    continue

                if session.file_system.folder_has_items(folder):
                    continue

                if not deleted_folder:
                    deleted_folder = True
                    self._logger.print()

                session.file_system.remove_folder(folder)

        self._unused_filter_tags = self._file_filter_factory.unused_filter_parts()

    def _session_for_config(self, config, file_system):
        base_path = config['base_path']
        if base_path not in self._sessions:
            new_session = _Session()
            new_session.new_files_not_overwritten = self._base_session.new_files_not_overwritten
            new_session.files_that_failed = self._base_session.files_that_failed
            new_session.processed_files = self._base_session.processed_files
            new_session.correctly_installed_files = self._base_session.correctly_installed_files
            new_session.file_system = file_system
            self._sessions[base_path] = new_session
        return self._sessions[base_path]

    def _print_db_header(self, db):
        self._logger.print()
        if len(db.header) > 0:
            self._logger.print('################################################################################')
            for line in db.header:
                if isinstance(line, float):
                    time.sleep(line)
                else:
                    self._logger.print(line, end='')
        else:
            self._logger.print('################################################################################')
            self._logger.print('SECTION: %s' % db.db_id)
            self._logger.print()

    def _create_file_filter(self, db, config):
        try:
            return self._file_filter_factory.create(db, config)
        except BadFileFilterPartException as e:
            raise WrongDatabaseOptions("Wrong custom download filter on database %s. Part '%s' is invalid." % (db.db_id, str(e)))

    def files_that_failed(self):
        return self._base_session.files_that_failed

    def unused_filter_tags(self):
        return self._unused_filter_tags

    def correctly_installed_files(self):
        return self._base_session.correctly_installed_files

    def needs_reboot(self):
        return any([session for session in self._sessions.values() if session.needs_reboot])

    def new_files_not_overwritten(self):
        return self._base_session.new_files_not_overwritten


class _OnlineZipSummaries:
    def __init__(self, db, store, full_resync, config, file_system, file_downloader_factory, logger, session):
        self._db = db
        self._store = store
        self._full_resync = full_resync
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._session = session

    def populate_db_with_summaries(self):
        removed_zip_ids = [zip_id for zip_id in self._store['zips'] if zip_id not in self._db.zips]
        if len(removed_zip_ids) > 0:
            self._remove_old_zip_ids(removed_zip_ids)

        zip_ids_from_store = []
        zip_ids_to_download = []

        for zip_id in self._db.zips:
            if zip_id in self._store['zips'] and self._store['zips'][zip_id]['summary_file']['hash'] == self._db.zips[zip_id]['summary_file']['hash']:
                zip_ids_from_store.append(zip_id)
            else:
                zip_ids_to_download.append(zip_id)

        if len(zip_ids_from_store) > 0:
            self._import_zip_ids_from_store(zip_ids_from_store)

        if len(zip_ids_to_download) > 0:
            self._import_zip_ids_from_network(zip_ids_to_download)

        return self._db

    def _remove_old_zip_ids(self, removed_zip_ids):
        for zip_id in removed_zip_ids:
            self._store['zips'].pop(zip_id)

        self._remove_non_zip_fields(self._store['files'].values(), removed_zip_ids)
        self._remove_non_zip_fields(self._store['folders'].values(), removed_zip_ids)

    @staticmethod
    def _remove_non_zip_fields(descriptions, removed_zip_ids):
        for description in descriptions:
            if 'zip_id' in description and description['zip_id'] in removed_zip_ids:
                description.pop('zip_id')
                if 'tags' in description:
                    description.pop('tags')

    def _import_zip_ids_from_network(self, zip_ids_to_download):
        summary_downloader = self._file_downloader_factory.create(self._config, self._config['parallel_update'])
        zip_ids_by_temp_zip = dict()

        for zip_id in zip_ids_to_download:
            temp_zip = '/tmp/%s_summary.json.zip' % zip_id
            zip_ids_by_temp_zip[temp_zip] = zip_id

            summary_downloader.queue_file(self._db.zips[zip_id]['summary_file'], temp_zip)

        summary_downloader.download_files(self._is_first_run())
        downloaded_summaries = [(zip_ids_by_temp_zip[temp_zip], temp_zip) for temp_zip in
                                summary_downloader.correctly_downloaded_files()]
        failed_zip_ids = [zip_ids_by_temp_zip[temp_zip] for temp_zip in summary_downloader.errors()]

        self._logger.print()

        for zip_id, temp_zip in downloaded_summaries:
            summary = self._file_system.load_dict_from_file(temp_zip)
            self._db.files.update(summary['files'])
            self._db.folders.update(summary['folders'])

            self._store['zips'][zip_id] = self._db.zips[zip_id]

            self._file_system.unlink(temp_zip)

        zip_ids_falling_back_to_store = [zip_id for zip_id in failed_zip_ids if zip_id in self._store['zips']]
        if len(zip_ids_falling_back_to_store) > 0:
            self._import_zip_ids_from_store(zip_ids_falling_back_to_store)

        self._session.files_that_failed.extend(summary_downloader.errors())

    def _import_zip_ids_from_store(self, zip_ids):
        self._db.files.update(self._entries_from_store('files', zip_ids))
        self._db.folders.update(self._entries_from_store('folders', zip_ids))

    def _entries_from_store(self, entry_kind, zip_ids):
        return {path: fd for path, fd in self._store[entry_kind].items() if 'zip_id' in fd and fd['zip_id'] in zip_ids}

    def _is_first_run(self):
        return len(self._store['files']) == 0


class _OnlineDatabaseImporter:
    def __init__(self, db, store, full_resync, config, file_system, file_downloader_factory, logger, session):
        self._db = db
        self._store = store
        self._full_resync = full_resync
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._session = session

    def process_db_contents(self):
        self._create_folders()

        self._remove_missing_files()

        file_downloader = self._file_downloader_factory.create(self._config, self._config['parallel_update'])
        file_downloader.set_base_files_url(self._db.base_files_url)
        needed_zips = dict()

        for file_path in self._db.files:
            self._assert_valid_path(file_path)

            if file_path in self._session.processed_files:
                self._logger.print('DUPLICATED: %s' % file_path)
                self._logger.print('Already been processed by database: %s' % self._session.processed_files[file_path])
                continue

            file_description = self._db.files[file_path]
            if not self._full_resync and file_path in self._store['files'] and \
                    self._store['files'][file_path]['hash'] == file_description['hash'] and \
                    self._should_not_download_again(file_path):
                self._store['files'][file_path] = file_description
                continue

            if 'overwrite' in file_description and not file_description['overwrite'] and self._file_system.is_file(file_path):
                if self._file_system.hash(file_path) != file_description['hash']:
                    self._session.add_new_file_not_overwritten(self._db.db_id, file_path)
                continue

            self._session.processed_files[file_path] = self._db.db_id

            if 'zip_id' in file_description:
                zip_id = file_description['zip_id']
                if zip_id not in needed_zips:
                    needed_zips[zip_id] = {'files': {}, 'total_size': 0}
                needed_zips[zip_id]['files'][file_path] = file_description
                needed_zips[zip_id]['total_size'] += file_description['size']

            file_downloader.queue_file(file_description, file_path)

        if len(needed_zips) > 0:
            self._import_zip_contents(needed_zips, file_downloader)

        file_downloader.download_files(self._is_first_run())

        for file_path in file_downloader.errors():
            if file_path in self._store['files']:
                self._store['files'].pop(file_path)

        self._session.files_that_failed.extend(file_downloader.errors())

        for path in file_downloader.correctly_downloaded_files():
            description = self._db.files[path]
            if 'tags' in description and 'zip_id' not in description:
                description.pop('tags')
            self._store['files'][path] = description

        self._session.correctly_installed_files.extend(file_downloader.correctly_downloaded_files())

        self._session.needs_reboot = self._session.needs_reboot or file_downloader.needs_reboot()

    def _assert_valid_path(self, path):
        if not isinstance(path, str):
            raise InvalidDownloaderPath(
                "Path is not a string '%s', contact with the author of the database." % str(path))

        if path == '' or path[0] == '/' or path[0] == '.' or path[0] == '\\':
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

        lower_path = path.lower()

        if lower_path in invalid_paths():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

        if self._db.db_id != distribution_mister_db_id and lower_path in no_distribution_mister_invalid_paths():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

        parts = lower_path.split('/')
        if '..' in parts or len(parts) == 0 or parts[0] in invalid_folders():
            raise InvalidDownloaderPath("Invalid path '%s', contact with the author of the database." % path)

    def _is_first_run(self):
        return len(self._store['files']) == 0

    def _import_zip_contents(self, needed_zips, file_downloader):
        zip_downloader = self._file_downloader_factory.create(self._config, self._config['parallel_update'])
        zip_ids_by_temp_zip = dict()
        for zip_id in needed_zips:
            zipped_files = needed_zips[zip_id]

            less_file_count = len(zipped_files['files']) < self._config['zip_file_count_threshold']
            less_accumulated_mbs = zipped_files['total_size'] < (1000 * 1000 * self._config['zip_accumulated_mb_threshold'])

            if less_file_count and less_accumulated_mbs:
                for file_path in zipped_files['files']:
                    file_downloader.queue_file(zipped_files['files'][file_path], file_path)
                self._store['zips'][zip_id] = self._db.zips[zip_id]
            else:
                temp_zip = '/tmp/%s_contents.zip' % zip_id
                zip_ids_by_temp_zip[temp_zip] = zip_id
                zip_downloader.queue_file(self._db.zips[zip_id]['contents_file'], temp_zip)

        if len(zip_ids_by_temp_zip) > 0:
            zip_downloader.download_files(self._is_first_run())
            self._logger.print()
            filtered_zip_data = self._store['filtered_zip_data'] if 'filtered_zip_data' in self._store else {}
            for temp_zip in sorted(zip_downloader.correctly_downloaded_files()):
                zip_id = zip_ids_by_temp_zip[temp_zip]
                path = self._db.zips[zip_id]['path']
                contents = ', '.join(self._db.zips[zip_id]['contents'])
                self._logger.print('Unpacking %s at %s' % (contents, 'the root' if path == './' else path))
                self._file_system.unzip_contents(temp_zip, self._db.zips[zip_id]['path'])
                self._file_system.unlink(temp_zip)
                file_downloader.mark_unpacked_zip(zip_id, self._db.zips[zip_id]['base_files_url'])
                if zip_id in filtered_zip_data:
                    for file_path in filtered_zip_data[zip_id]['files']:
                        self._file_system.unlink(file_path)
                    for folder_path in sorted(filtered_zip_data[zip_id]['folders'].keys(), key=len, reverse=True):
                        if not self._file_system.is_folder(folder_path):
                            continue
                        if self._file_system.folder_has_items(folder_path):
                            continue
                        self._file_system.remove_folder(folder_path)

                self._store['zips'][zip_id] = self._db.zips[zip_id]
            self._logger.print()
            self._session.files_that_failed.extend(zip_downloader.errors())

    def _should_not_download_again(self, file_path):
        if not self._config['check_manually_deleted_files']:
            return True

        return self._file_system.is_file(file_path)

    def _create_folders(self):
        for folder in self._db.folders:
            self._assert_valid_path(folder)
            self._file_system.make_dirs(folder)

        self._session.dbs_folders |= set(self._db.folders)
        self._session.stores_folders |= set(self._store['folders'])

        self._store['folders'] = self._db.folders

        for description in self._store['folders'].values():
            if 'tags' in description and 'zip_id' not in description:
                description.pop('tags')

    def _remove_missing_files(self):
        store_files, db_files = self._store['files'], self._db.files

        files_to_delete = [f for f in store_files if f not in db_files]

        for file_path in files_to_delete:
            self._file_system.unlink(file_path)

            if file_path in store_files:
                store_files.pop(file_path)

        if len(files_to_delete) > 0:
            self._logger.print()


class InvalidDownloaderPath(Exception):
    pass


class WrongDatabaseOptions(Exception):
    pass


def no_distribution_mister_invalid_paths():
    return ('mister', 'menu.rbf')


def invalid_paths():
    return ('mister.ini', 'mister_alt.ini', 'mister_alt_1.ini', 'mister_alt_2.ini', 'mister_alt_3.ini', 'scripts/downloader.sh', 'mister.new')


def invalid_folders():
    return ('linux', 'saves', 'savestates', 'screenshots')
