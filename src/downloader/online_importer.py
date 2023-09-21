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

from typing import Dict, Set

from downloader.config import download_sensitive_configs
from downloader.constants import K_BASE_PATH, K_ZIP_FILE_COUNT_THRESHOLD,\
    K_ZIP_ACCUMULATED_MB_THRESHOLD, FILE_MiSTer_new, FILE_MiSTer, FILE_MiSTer_old, K_BASE_SYSTEM_PATH
from downloader.file_filter import BadFileFilterPartException
from downloader.file_system import FolderCreationError, ReadOnlyFileSystem, UnlinkTemporaryException, FileCopyError
from downloader.free_space_reservation import FreeSpaceReservation
from downloader.other import UnreachableException, calculate_url


class _Session:
    def __init__(self):
        self.files_that_failed = []
        self.files_that_failed_from_zip = []
        self.folders_that_failed = []
        self.zips_that_failed = []
        self.correctly_installed_files = []
        self.new_files_not_overwritten = {}
        self.processed_files = {}
        self.needs_reboot = False
        self.file_system = None

    def add_new_file_not_overwritten(self, db_id, file):
        if db_id not in self.new_files_not_overwritten:
            self.new_files_not_overwritten[db_id] = []
        self.new_files_not_overwritten[db_id].append(file)


class OnlineImporter:
    def __init__(self, file_filter_factory, file_system_factory, file_downloader_factory, path_resolver_factory,
                 local_repository, external_drives_repository, free_space_reservation: FreeSpaceReservation, waiter, logger):
        self._file_filter_factory = file_filter_factory
        self._file_system_factory = file_system_factory
        self._file_downloader_factory = file_downloader_factory
        self._path_resolver_factory = path_resolver_factory
        self._local_repository = local_repository
        self._external_drives_repository = external_drives_repository
        self._free_space_reservation = free_space_reservation
        self._waiter = waiter
        self._logger = logger
        self._unused_filter_tags = []
        self._full_partitions = []
        self._base_session = _Session()

    def download_dbs_contents(self, importer_command, full_resync):
        # TODO: Move the filter validation to earlier (before downloading dbs).
        self._logger.bench('Online Importer start.')

        packages = self._unpack_dbs_data(importer_command, full_resync)
        self._process_already_present_files(packages)
        not_fitting_files = self._filter_not_fitting_files()
        self._create_folders(packages)
        config_map = self._build_config_map(packages)
        self._process_config_map(config_map, not_fitting_files)
        self._remove_files(packages)
        self._finish_stores(packages)
        self._remove_folders(importer_command)
        self._unused_filter_tags = self._file_filter_factory.unused_filter_parts()
        self._clean_stores(importer_command)

        self._logger.bench('Online Importer done.')

    def _unpack_dbs_data(self, importer_command, full_resync):
        packages = []

        self._logger.print("Preparing databases ...")

        for db, store, config in importer_command.read_dbs():
            read_only_store = store.read_only()

            self._logger.debug(f"Preparing db '{db.db_id}'...")
            file_system = ReadOnlyFileSystem(self._file_system_factory.create_for_config(config))

            self._logger.bench('Restoring filtered ZIP data...')
            restored_db = _OnlineFilteredZipData(db, read_only_store).restore_filtered_zip_data()

            self._logger.bench('Expanding summaries...')
            zip_summaries_expander = _OnlineZipSummaries(restored_db, read_only_store, full_resync, config, file_system, self._file_downloader_factory, self._logger, self._base_session)
            expanded_db, zip_summaries = zip_summaries_expander.expand_summaries()

            self._logger.bench('Filtering Database...')
            file_filter = self._create_file_filter(expanded_db, config)
            filtered_db, filtered_zip_data = file_filter.select_filtered_files(expanded_db)

            externals = {'priority_files': {}, 'priority_sub_folders': {}, 'priority_top_folders': {}}

            self._logger.bench('Translating paths...')
            path_resolver = self._path_resolver_factory.create(config, externals['priority_top_folders'])
            resolver = _Resolver(filtered_db, read_only_store, config, path_resolver, self._local_repository, self._logger, self._base_session, externals)
            resolved_db = resolver.translate_paths()

            db_file_selector = _DatabaseFileSelector(resolved_db, read_only_store, full_resync, file_system, self._logger, self._base_session, self._free_space_reservation)

            self._logger.bench('Selecting changed files...')
            changed_files, already_present_files, needed_zips = db_file_selector.select_changed_files()

            packages.append((resolved_db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries))

        return packages

    def _process_already_present_files(self, packages):
        for db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries in packages:
            self._logger.bench(f'Process {db.db_id} already present files...')

            read_only_store = store.read_only()
            write_only_store = store.write_only()

            file_system = self._file_system_factory.create_for_config(config)
            db_importer = _OnlineDatabaseImporter(db, write_only_store, read_only_store, externals, config, file_system, self._file_downloader_factory, self._logger, self._base_session, self._external_drives_repository)

            db_importer.process_already_present_files(already_present_files)

    def _filter_not_fitting_files(self) -> Set[str]:
        self._logger.debug(f"Free space: {self._free_space_reservation.free_space()}")

        full_partitions = self._free_space_reservation.get_full_partitions()
        if len(full_partitions) == 0:
            return set()

        self._logger.bench(f'Filtering out not fitting files...')

        not_fitting_files = set()
        for partition in full_partitions:
            self._logger.print(f"Partition {partition.partition_path} is full!")
            self._full_partitions.append(partition.partition_path)
            not_fitting_files.update(partition.files)

        return not_fitting_files

    def _create_folders(self, packages):
        for db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries in packages:
            self._logger.bench(f'Creating db {db.db_id} folders...')

            read_only_store = store.read_only()
            write_only_store = store.write_only()

            file_system = self._file_system_factory.create_for_config(config)
            db_importer = _OnlineDatabaseImporter(db, write_only_store, read_only_store, externals, config, file_system, self._file_downloader_factory, self._logger, self._base_session, self._external_drives_repository)
            db_importer.create_folders()

    def _build_config_map(self, packages):
        self._logger.debug(f"Building config map...")
        config_map = {}
        for db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries in packages:
            config_key = ''
            for key in download_sensitive_configs():
                config_key += f'{key}:{str(config[key])};'

            if config_key not in config_map:
                config_map[config_key] = []
            config_map[config_key].append((db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries))

        return config_map

    def _process_config_map(self, config_map, not_fitting_files: Set[str]):
        for config_json, subpackages in config_map.items():
            self._logger.debug(f"Processing config '{config_json}'...")
            config = None if len(subpackages) == 0 else subpackages[0][1]
            file_system = self._file_system_factory.create_for_config(config)
            file_downloader = self._file_downloader_factory.create(config, parallel_update=True)

            files_to_download = []
            store_by_file = {}
            is_first_run = False

            for db, _config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries in subpackages:
                self._logger.bench(f'Process db {db.db_id} changed files...')

                read_only_store = store.read_only()
                write_only_store = store.write_only()

                if len(changed_files) > 0:
                    files_to_download.append((f'[{db.db_id}]', {'db': db}))
                else:
                    self._print_db_header(db)
                    self._logger.print("Nothing new to download from given sources.")

                db_importer = _OnlineDatabaseImporter(db, write_only_store, read_only_store, externals, config, file_system, self._file_downloader_factory, self._logger, self._base_session,
                                                      self._external_drives_repository)

                for file_path, file_description in changed_files.items():
                    download_description = {'hash': file_description['hash'], 'size': file_description['size']}
                    if 'url' in file_description:
                        download_description['url'] = file_description['url']

                    base_files_url = db.base_files_url
                    if 'zip_id' in file_description and file_description['zip_id'] in db.zips:
                        zip_id = file_description['zip_id']
                        download_description['zip_id'] = zip_id
                        if 'zip_path' in file_description:
                            download_description['zip_path'] = file_description['zip_path']
                        zip_base_files_url = db.zips[zip_id].get('base_files_url', None)
                        if zip_base_files_url is not None and len(zip_base_files_url) > 0:
                            base_files_url = zip_base_files_url

                    if 'url' not in download_description:
                        maybe_url = calculate_url(base_files_url, file_path)
                        if maybe_url is not None:
                            download_description['url'] = maybe_url

                    files_to_download.append((file_path, download_description))
                    store_by_file[file_path] = [write_only_store, db_importer, file_description]

                is_first_run = is_first_run or db_importer._is_first_run()
                if len(needed_zips) > 0:
                    db_importer._import_zip_contents(needed_zips, filtered_zip_data, file_downloader, not_fitting_files)

            if len(files_to_download) == 0:
                continue

            not_downloaded_files = []
            for file_path, download_description in files_to_download:
                if 'size' in download_description and file_system.download_target_path(file_path) in not_fitting_files:
                    not_downloaded_files.append(file_path)
                    continue
                file_downloader.queue_file(download_description, file_path)

            self._logger.print("\nDownloading %d files:" % len(files_to_download))
            file_downloader.download_files(is_first_run)

            self._base_session.files_that_failed.extend(file_downloader.errors() + not_downloaded_files)
            self._base_session.folders_that_failed.extend(file_downloader.failed_folders())
            self._base_session.correctly_installed_files.extend(file_downloader.correctly_downloaded_files())

            for file_path in file_downloader.errors():
                write_only_store, db_importer, file_description = store_by_file[file_path]
                write_only_store.remove_file(file_path)

            for file_path in file_downloader.correctly_downloaded_files():
                write_only_store, db_importer, file_description = store_by_file[file_path]
                if file_description.get('reboot', False):
                    self._base_session.needs_reboot = True
                db_importer._add_file_to_store(file_path, file_description)

            for file_path in set(self._base_session.files_that_failed_from_zip) - set(file_downloader.correctly_downloaded_files()):
                write_only_store, db_importer, file_description = store_by_file[file_path]
                db_importer._add_file_to_store(file_path, file_description)

    def _remove_files(self, packages):
        for db, config, store, externals, changed_files, already_present_files, needed_zips, filtered_zip_data, zip_summaries in packages:
            self._logger.bench(f'Remove db {db.db_id} deleted files...')

            read_only_store = store.read_only()
            write_only_store = store.write_only()

            file_system = self._file_system_factory.create_for_config(config)
            db_importer = _OnlineDatabaseImporter(db, write_only_store, read_only_store, externals, config, file_system, self._file_downloader_factory, self._logger, self._base_session, self._external_drives_repository)

            db_importer.remove_deleted_files()

    def _finish_stores(self, packages):
        for db, config, store, _externals, _changed_files, _already_present_files, _needed_zips, filtered_zip_data, zip_summaries in packages:
            self._logger.bench(f'Finishing db {db.db_id} store...')

            write_only_store = store.write_only()
            write_only_store.populate_with_summary(zip_summaries, db.zips)
            write_only_store.drop_removed_zips_from_store(db.zips)
            write_only_store.save_filtered_zip_data(filtered_zip_data)
            write_only_store.set_base_path(config[K_BASE_PATH])

    def _clean_stores(self, importer_command):
        self._logger.bench('Cleaning stores...')

        for _, store, config in importer_command.read_dbs():
            write_store = store.write_only()
            read_store = store.read_only()

            file_system = self._file_system_factory.create_for_config(config)
            if read_store.has_externals:
                for drive in read_store.external_drives:
                    write_store.try_cleanup_drive(drive)

                write_store.try_cleanup_externals()

            delete_files = []
            for file_path, file_description in read_store.files.items():
                if 'zip_id' in file_description and file_path in self._base_session.files_that_failed_from_zip:
                    continue

                if is_system_path(file_description):
                    present_file_path = f'{config[K_BASE_SYSTEM_PATH]}/{file_path}'
                else:
                    present_file_path = f'{config[K_BASE_PATH]}/{file_path}'

                if file_system.is_file(present_file_path):
                    continue

                delete_files.append(file_path)
            for file_path in delete_files:
                write_store.remove_file(file_path)

            delete_folders = []
            for folder_path in sorted(read_store.folders, key=len, reverse=True):

                folder_description = read_store.folders[folder_path]
                if is_system_path(folder_description) and \
                        file_system.is_folder('%s/%s' % (config[K_BASE_SYSTEM_PATH], folder_path)):
                    continue
                elif file_system.is_folder('%s/%s' % (config[K_BASE_PATH], folder_path)):
                    continue

                delete_folders.append(folder_path)
            for folder_path in delete_folders:
                write_store.remove_folder(folder_path)

    def _remove_folders(self, importer_command):
        self._logger.bench('Removing folders...')

        store_by_id = {}
        db_folders = {}
        internal_store_folders = {}
        external_stored_folders = {}

        # fill up trans-db folder registries

        for db, store, config in importer_command.read_dbs():
            read_only_store = store.read_only()

            store_by_id[db.db_id] = store

            for folder_path in db.folders:
                if folder_path not in db_folders:
                    db_folders[folder_path] = set()

                db_folders[folder_path].add(db.db_id)

            for folder_path, folder_description in read_only_store.folders.items():
                base_path = config[K_BASE_PATH]
                if is_system_path(folder_description):
                    base_path = config[K_BASE_SYSTEM_PATH]

                if base_path not in internal_store_folders:
                    internal_store_folders[base_path] = {}

                if folder_path not in internal_store_folders[base_path]:
                    internal_store_folders[base_path][folder_path] = set()

                internal_store_folders[base_path][folder_path].add(db.db_id)

            if not read_only_store.has_externals:
                continue

            for drive, external in read_only_store.externals:
                for folder_path in external['folders']:
                    if drive not in external_stored_folders:
                        external_stored_folders[drive] = {}

                    if folder_path not in external_stored_folders[drive]:
                        external_stored_folders[drive][folder_path] = set()

                    external_stored_folders[drive][folder_path].add(db.db_id)

        # remove folders from fs
        system_file_system = self._file_system_factory.create_for_system_scope()

        for drive, folders in internal_store_folders.items():
            for folder_path in sorted(folders, key=len, reverse=True):
                if folder_path in db_folders:
                    continue

                full_folder_path = '%s/%s' % (drive, folder_path)
                if system_file_system.folder_has_items(full_folder_path):
                    continue

                system_file_system.remove_folder(full_folder_path)
                for db_id in folders[folder_path]:
                    store_by_id[db_id].write_only().remove_folder(folder_path)

        for drive, folders in external_stored_folders.items():
            for folder_path in sorted(folders, key=len, reverse=True):
                if folder_path in db_folders:
                    continue

                if len(folder_path.split('/')) <= 2:  # when storage_priority is prefer_sd
                    continue

                full_folder_path = '%s/%s' % (drive, folder_path)
                if system_file_system.folder_has_items(full_folder_path):
                    continue

                system_file_system.remove_folder(full_folder_path)
                for db_id in folders[folder_path]:
                    store_by_id[db_id].write_only().remove_external_folder(drive, folder_path)

        # remove folders from store
        for db, store, config in importer_command.read_dbs():
            read_store = store.read_only()
            write_store = store.write_only()

            for folder_path in sorted(list(read_store.folders), key=len, reverse=True):
                if folder_path in db.folders:
                    continue

                folder_description = read_store.folders[folder_path]
                if is_system_path(folder_description) and \
                        system_file_system.folder_has_items(f'{config[K_BASE_SYSTEM_PATH]}/{folder_path}'):
                    continue
                elif system_file_system.folder_has_items(f'{config[K_BASE_PATH]}/{folder_path}'):
                    continue

                write_store.remove_folder(folder_path)

            if not read_store.has_externals:
                continue

            for drive in read_store.external_drives:
                delete_folders = []
                external_folders = read_store.external_folders(drive)
                for folder_path in sorted(external_folders, key=len, reverse=True):
                    if folder_path in db_folders:
                        continue

                    # Note on following folder_has_items call:
                    #
                    # A folder_description coming from store.external_folders() can never be a system path,
                    # so we only check K_BASE_PATH and ignore K_BASE_SYSTEM_PATH
                    #
                    # If it's a system path, it's a bug but will be ignored. Note that we are filtering this cases out
                    # currently during the translation step. So it's very unlikely to happen,
                    # and there is no real damage if it occurs.

                    if system_file_system.folder_has_items(f'{config[K_BASE_PATH]}/{folder_path}'):
                        continue

                    delete_folders.append(folder_path)

                for folder_path in delete_folders:
                    write_store.remove_external_folder(drive, folder_path)

    def _print_db_header(self, db):
        self._logger.print()
        if len(db.header) > 0:
            self._logger.print('################################################################################')
            for line in db.header:
                if isinstance(line, float):
                    self._waiter.sleep(line)
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
            raise WrongDatabaseOptions(
                "Wrong custom download filter on database %s. Part '%s' is invalid." % (db.db_id, str(e)))

    def files_that_failed(self):
        return self._base_session.files_that_failed

    def folders_that_failed(self):
        return self._base_session.folders_that_failed

    def zips_that_failed(self):
        return self._base_session.zips_that_failed

    def unused_filter_tags(self):
        return self._unused_filter_tags

    def correctly_installed_files(self):
        return self._base_session.correctly_installed_files

    def needs_reboot(self):
        return self._base_session.needs_reboot

    def full_partitions(self):
        return self._full_partitions

    def new_files_not_overwritten(self):
        return self._base_session.new_files_not_overwritten


class _Resolver:
    def __init__(self, db, read_only_store, config, path_resolver, local_repository, logger, session, externals):
        self._db = db
        self._read_only_store = read_only_store
        self._config = config
        self._path_resolver = path_resolver
        self._local_repository = local_repository
        self._logger = logger
        self._session = session
        self._externals = externals

    def _is_external_zip(self, path, description):
        if path[0] == '|' or 'zip_id' not in description:
            return False

        zip_id = description['zip_id']
        zip_descr = self._db.zips[zip_id]
        if 'target_folder_path' not in zip_descr or len(zip_descr['target_folder_path']) == 0:
            return False

        return zip_descr['target_folder_path'][0] == '|'

    def translate_paths(self):
        priority_files = self._externals['priority_files']
        priority_sub_folders = self._externals['priority_sub_folders']

        input_folders = self._db.folders
        self._db.folders = {}
        for target_folder_path, description in input_folders.items():
            self._translate_input_folder_path(description, priority_sub_folders, target_folder_path)

        input_files = self._db.files
        self._db.files = {}
        for file_path, description in input_files.items():
            self._translate_input_file_path(description, file_path, priority_files)

        input_zips = self._db.zips
        self._db.zips = {}
        for zip_id, zip_description in input_zips.items():
            self._translate_input_zip_paths(priority_sub_folders, zip_id, zip_description)

        return self._db

    def _translate_input_zip_paths(self, priority_sub_folders, zip_id, zip_description):
        kind = zip_description['kind']
        if kind == 'extract_all_contents':
            if is_system_path(zip_description):
                self._logger.print('ERROR: Zip %s is marked as system path, contact the db maintainer. Skipping...' % zip_id)
                self._logger.debug(zip_description)
                self._session.zips_that_failed.append(zip_id)
                return

            target_zip_folder_path = zip_description['target_folder_path']
            target_zip_folder_base_path = self._path_resolver.resolve_folder_path(target_zip_folder_path)
            if target_zip_folder_path[0] == '|':
                target_zip_folder_path = target_zip_folder_path[1:]
            if target_zip_folder_base_path is not None and self._read_only_store.base_path != target_zip_folder_base_path:
                priority_sub_folders[target_zip_folder_path] = target_zip_folder_base_path

        self._db.zips[zip_id] = zip_description

    def _translate_input_file_path(self, description, file_path, priority_files):
        target_is_system_path = is_system_path(description)
        if self._is_external_zip(file_path, description):
            file_path = '|' + file_path

        if file_path[0] == '|':
            if target_is_system_path:
                self._logger.print('ERROR: External file %s is marked as system path, contact the db maintainer. Skipping...' % file_path)
                self._logger.debug(description)
                self._session.files_that_failed.append(file_path[1:])
                return
            base_path = self._path_resolver.resolve_file_path(file_path)
            file_path = file_path[1:]
        else:
            if target_is_system_path:
                self._path_resolver.add_system_path(file_path)
                if file_path == FILE_MiSTer:
                    self._path_resolver.add_system_path(FILE_MiSTer_new)
                    self._path_resolver.add_system_path(FILE_MiSTer_old)

                    self._path_resolver.resolve_file_path(FILE_MiSTer_new)
                    self._path_resolver.resolve_file_path(FILE_MiSTer_old)
            base_path = self._path_resolver.resolve_file_path(file_path)

        if base_path is not None and self._read_only_store.base_path != base_path and not target_is_system_path:
            priority_files[file_path] = base_path
        self._db.files[file_path] = description

    def _translate_input_folder_path(self, description, priority_sub_folders, target_folder_path):
        is_external_zip = self._is_external_zip(target_folder_path, description)
        target_is_system_path = is_system_path(description)
        if is_external_zip:
            target_folder_path = '|' + target_folder_path

        if target_folder_path[0] == '|':
            if target_is_system_path:
                self._logger.print('ERROR: External folder %s is marked as system path, contact the db maintainer. Skipping...' % target_folder_path)
                self._logger.debug(description)
                self._session.folders_that_failed.append(target_folder_path[1:])
                return

            base_path = self._path_resolver.resolve_folder_path(target_folder_path)
            target_folder_path = target_folder_path[1:]
        else:
            if target_is_system_path:
                self._path_resolver.add_system_path(target_folder_path)
            base_path = self._path_resolver.resolve_folder_path(target_folder_path)

        if base_path is not None and self._read_only_store.base_path != base_path and not target_is_system_path:
            priority_sub_folders[target_folder_path] = base_path
        self._db.folders[target_folder_path] = description


class _OnlineFilteredZipData:
    def __init__(self, db, read_only_store):
        self._db = db
        self._read_only_store = read_only_store

    def restore_filtered_zip_data(self):
        for zip_id, zip_data in self._read_only_store.filtered_zip_data.items():
            if zip_id not in self._db.zips:
                continue

            self._db.files.update(zip_data['files'])
            self._db.folders.update(zip_data['folders'])

        return self._db


class _OnlineZipSummaries:
    def __init__(self, db, read_only_store, full_resync, config, file_system, file_downloader_factory, logger, session):
        self._db = db
        self._read_only_store = read_only_store
        self._full_resync = full_resync
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._session = session

    def expand_summaries(self):
        zip_ids_from_store = []
        zip_ids_to_download = []
        zip_ids_from_internal_summary = []

        for zip_id, db_zip_desc in self._db.zips.items():
            if is_system_path(db_zip_desc):
                continue

            if 'summary_file' in db_zip_desc:
                db_summary_file_hash = db_zip_desc['summary_file']['hash']
                store_summary_file_hash = self._store_summary_file_hash_by_zip_id(zip_id)
                if store_summary_file_hash is not None and store_summary_file_hash == db_summary_file_hash:
                    zip_ids_from_store.append(zip_id)
                else:
                    zip_ids_to_download.append(zip_id)
            elif 'internal_summary' in db_zip_desc:
                zip_ids_from_internal_summary.append(zip_id)
            else:
                raise UnreachableException(
                    'Unreachable code path for: %s.%s' % (self._db.db_id, zip_id))  # pragma: no cover

        summaries = []
        if len(zip_ids_from_internal_summary) > 0:
            summaries.extend(self._import_zip_ids_from_internal_summaries(zip_ids_from_internal_summary))

        if len(zip_ids_from_store) > 0:
            self._import_zip_ids_from_store(zip_ids_from_store)

        if len(zip_ids_to_download) > 0:
            summaries.extend(self._import_zip_ids_from_network(zip_ids_to_download))

        return self._db, summaries

    def _store_summary_file_hash_by_zip_id(self, zip_id):
        store_zip_desc = self._read_only_store.zip_description(zip_id)
        store_summary_file = store_zip_desc['summary_file'] if 'summary_file' in store_zip_desc else {}
        return store_summary_file['hash'] if 'hash' in store_summary_file else None

    def _import_zip_ids_from_internal_summaries(self, zip_ids_from_internal_summaries):
        summaries = []
        for zip_id in zip_ids_from_internal_summaries:
            summary = self._db.zips[zip_id]['internal_summary']
            self._populate_with_summary(zip_id, summary)
            self._db.zips[zip_id].pop('internal_summary')
            summaries.append((zip_id, summary))

        return summaries

    def _import_zip_ids_from_network(self, zip_ids_to_download):
        summary_downloader = self._file_downloader_factory.create(self._config, parallel_update=True, silent=True)
        zip_ids_by_temp_zip = dict()

        temp_filename = self._file_system.unique_temp_filename()
        for zip_id in zip_ids_to_download:
            temp_zip = '%s_%s_summary.json.zip' % (temp_filename.value, zip_id)
            zip_ids_by_temp_zip[temp_zip] = zip_id

            summary_downloader.queue_file(self._db.zips[zip_id]['summary_file'], temp_zip)

        temp_filename.close()

        summary_downloader.download_files(self._is_first_run())
        downloaded_summaries = [(zip_ids_by_temp_zip[temp_zip], temp_zip) for temp_zip in
                                summary_downloader.correctly_downloaded_files()]
        failed_zip_ids = [zip_ids_by_temp_zip[temp_zip] for temp_zip in summary_downloader.errors()]

        summaries = []
        for zip_id, temp_zip in downloaded_summaries:
            summary = self._file_system.load_dict_from_file(temp_zip)
            self._populate_with_summary(zip_id, summary)
            self._file_system.unlink(temp_zip, exception=UnlinkTemporaryException())
            summaries.append((zip_id, summary))

        zip_ids_falling_back_to_store = [zip_id for zip_id in failed_zip_ids if zip_id in self._read_only_store.zips]
        if len(zip_ids_falling_back_to_store) > 0:
            self._import_zip_ids_from_store(zip_ids_falling_back_to_store)

        self._session.files_that_failed.extend(summary_downloader.errors())
        self._session.folders_that_failed.extend(summary_downloader.failed_folders())

        return summaries

    def _populate_with_summary(self, zip_id, summary):
        self._db.files.update(summary['files'])
        self._db.folders.update(summary['folders'])

    def _import_zip_ids_from_store(self, zip_ids):
        self._db.files.update(self._read_only_store.entries_in_zip('files', zip_ids))
        self._db.folders.update(self._read_only_store.entries_in_zip('folders', zip_ids))

    def _is_first_run(self):
        return self._read_only_store.has_no_files


class _DatabaseFileSelector:
    def __init__(self, db, read_only_store, full_resync, file_system, logger, session, free_space_reservation: FreeSpaceReservation):
        self._db = db
        self._read_only_store = read_only_store
        self._full_resync = full_resync
        self._file_system = file_system
        self._logger = logger
        self._session = session
        self._free_space_reservation = free_space_reservation

    def select_changed_files(self):
        changed_files = {}
        already_present_files = {}
        needed_zips = {}

        for file_path, file_description in self._db.files.items():
            if file_path in self._session.processed_files:
                self._logger.print('DUPLICATED: %s' % file_path)
                self._logger.print('Already been processed by database: %s' % self._session.processed_files[file_path])
                continue

            if self._file_system.is_file(file_path):
                store_hash = self._read_only_store.hash_file(file_path)

                if not self._full_resync and store_hash == file_description['hash']:
                    already_present_files[file_path] = [file_description, True]
                    continue

                if store_hash == 'file_does_not_exist_so_cant_get_hash' and self._file_system.hash(file_path) == file_description['hash']:
                    already_present_files[file_path] = [file_description, False]
                    continue

                if 'overwrite' in file_description and not file_description['overwrite']:
                    if self._file_system.hash(file_path) != file_description['hash']:
                        self._session.add_new_file_not_overwritten(self._db.db_id, file_path)
                    continue

            changed_files[file_path] = file_description
            self._session.processed_files[file_path] = self._db.db_id
            self._free_space_reservation.reserve_space_for_file(self._file_system.download_target_path(file_path), file_description)

            if 'zip_id' not in file_description:
                continue

            zip_id = file_description['zip_id']
            if zip_id not in needed_zips:
                needed_zips[zip_id] = {'files': {}, 'total_size': 0}
            needed_zips[zip_id]['files'][file_path] = file_description
            needed_zips[zip_id]['total_size'] += file_description['size']

        return changed_files, already_present_files, needed_zips


class _OnlineDatabaseImporter:
    def __init__(self, db, write_only_store, read_only_store, externals, config, file_system,
                 file_downloader_factory, logger, session, external_drives_repository):
        self._db = db
        self._write_only_store = write_only_store
        self._read_only_store = read_only_store
        self._externals = externals
        self._config = config
        self._file_system = file_system
        self._file_downloader_factory = file_downloader_factory
        self._logger = logger
        self._session = session
        self._external_drives_repository = external_drives_repository

    def process_already_present_files(self, already_existing_files):
        for file_path, [file_description, has_matching_hash] in already_existing_files.items():
            self._add_file_to_store(file_path, file_description)
            if has_matching_hash:
                continue

            self._logger.print('No changes: %s' % file_path)
            self._session.correctly_installed_files.append(file_path)
            self._session.processed_files[file_path] = self._db.db_id

    def process_changed_files(self, changed_files, needed_zips, filtered_zip_data):
        file_downloader = self._file_downloader_factory.create(self._config, parallel_update=True)
        file_downloader.set_base_files_url(self._db.base_files_url)

        for file_path, file_description in changed_files.items():
            file_downloader.queue_file(file_description, file_path)

        if len(needed_zips) > 0:
            self._import_zip_contents(needed_zips, filtered_zip_data, file_downloader)

        file_downloader.download_files(self._is_first_run())

        self._session.files_that_failed.extend(file_downloader.errors())
        self._session.folders_that_failed.extend(file_downloader.failed_folders())
        self._session.correctly_installed_files.extend(file_downloader.correctly_downloaded_files())

        for file_path in file_downloader.errors():
            self._write_only_store.remove_file(file_path)

        for file_path in file_downloader.correctly_downloaded_files():
            if changed_files[file_path].get('reboot', False):
                self._session.needs_reboot = True
            self._add_file_to_store(file_path, changed_files[file_path])

    def _add_file_to_store(self, file_path, file_description):
        if 'tags' in file_description and 'zip_id' not in file_description:
            file_description.pop('tags')

        if file_path in self._externals['priority_files']:
            self._write_only_store.add_external_file(self._externals['priority_files'][file_path], file_path, file_description)
        else:
            self._write_only_store.add_file(file_path, file_description)

    def _is_first_run(self):
        return self._read_only_store.has_no_files

    def _import_zip_contents(self, needed_zips, filtered_zip_data, file_downloader, not_fitting_files):
        zip_downloader = self._file_downloader_factory.create(self._config, parallel_update=True)
        zip_ids_by_temp_zip = dict()

        temp_filename = self._file_system.unique_temp_filename()

        for zip_id in needed_zips:
            zipped_files = needed_zips[zip_id]

            needs_extracting_single_files = 'kind' in self._db.zips[zip_id] and self._db.zips[zip_id]['kind'] == 'extract_single_files'
            less_file_count = len(zipped_files['files']) < self._config[K_ZIP_FILE_COUNT_THRESHOLD]
            less_accumulated_mbs = zipped_files['total_size'] < (1000 * 1000 * self._config[K_ZIP_ACCUMULATED_MB_THRESHOLD])

            if not needs_extracting_single_files and less_file_count and less_accumulated_mbs:
                continue

            if len(not_fitting_files):
                any_not_fitting = False
                for file_path in zipped_files['files']:
                    if self._file_system.download_target_path(file_path) in not_fitting_files:
                        self._session.files_that_failed_from_zip.append(file_path)
                        any_not_fitting = True

                if any_not_fitting:
                    continue

            temp_zip = '%s_%s_contents.zip' % (temp_filename.value, zip_id)
            zip_ids_by_temp_zip[temp_zip] = zip_id
            zip_downloader.queue_file(self._db.zips[zip_id]['contents_file'], temp_zip)

        temp_filename.close()

        if len(zip_ids_by_temp_zip) == 0:
            return

        zip_downloader.download_files(self._is_first_run())
        for temp_zip in sorted(zip_downloader.correctly_downloaded_files()):
            zip_id = zip_ids_by_temp_zip[temp_zip]
            zipped_files = needed_zips[zip_id]
            zip_description = self._db.zips[zip_id]

            self._import_zip_contents_from_temp_zip(temp_zip, zip_id, zipped_files, zip_description, filtered_zip_data, file_downloader)

        self._session.files_that_failed.extend(zip_downloader.errors())

    def _import_zip_contents_from_temp_zip(self, temp_zip, zip_id, zipped_files, zip_description, filtered_zip_data, file_downloader):
        kind = zip_description['kind']
        if kind == 'extract_all_contents':
            target_folder_path = zip_description['target_folder_path']
            if target_folder_path[0] == '|':
                target_folder_path = target_folder_path[1:]

            self._logger.print(zip_description['description'])
            self._file_system.unzip_contents(temp_zip, target_folder_path, list(zipped_files['files']))
            self._file_system.unlink(temp_zip)
            file_downloader.mark_unpacked_zip(zip_id, zip_description['base_files_url'])

            filtered_files = filtered_zip_data[zip_id]['files'] if zip_id in filtered_zip_data else []
            for file_path in filtered_files:
                self._file_system.unlink(file_path)

            # TODO: Add this back when adding official support fort zips
            # for folder_path in sorted(filtered_zip_data[zip_id]['folders'].keys(), key=len, reverse=True):
            #     if not self._file_system.is_folder(folder_path):
            #         continue
            #     if self._file_system.folder_has_items(folder_path):
            #         continue
            #
            #     self._file_system.remove_folder(folder_path)

        elif kind == 'extract_single_files':
            self._logger.print(zip_description['description'])
            temp_filename = self._file_system.unique_temp_filename()
            tmp_path = '%s_%s/' % (temp_filename.value, zip_id)
            self._file_system.unzip_contents(temp_zip, tmp_path, list(zipped_files['files']))
            for file_path, file_description in zipped_files['files'].items():
                try:
                    self._file_system.copy('%s%s' % (tmp_path, file_description['zip_path']), file_path)
                except FileCopyError as _e:
                    self._session.files_that_failed_from_zip.append(file_path)
                    self._logger.print('ERROR: File "%s" could not be copied, skipping.' % file_path)

            self._file_system.unlink(temp_zip)
            self._file_system.remove_non_empty_folder(tmp_path)
            temp_filename.close()
            file_downloader.mark_unpacked_zip(zip_id, 'whatever')
        else:
            raise UnreachableException('ERROR: ZIP %s has wrong field kind "%s", contact the db maintainer.' % (zip_id, kind))  # pragma: no cover

    def create_folders(self):
        for folder_path in sorted(self._db.folders):
            folder_description = self._db.folders[folder_path]

            try:
                self._create_folder_in_folders(folder_path, folder_description)
            except FolderCreationError as _e:
                self._logger.print('ERROR: Folder "%s" could not be created, skipping.' % folder_path)
                self._session.folders_that_failed.append(folder_path)

    def _create_folder_in_folders(self, folder_path, folder_description):
        priority_top_folders = self._externals['priority_top_folders']
        priority_sub_folders = self._externals['priority_sub_folders']

        if 'tags' in folder_description and 'zip_id' not in folder_description:
            folder_description.pop('tags')

        if folder_path in priority_top_folders:
            for drive in priority_top_folders[folder_path].drives:
                self._write_folder(drive, folder_path, folder_description)
        elif folder_path in priority_sub_folders:
            drive = priority_sub_folders[folder_path]
            self._write_folder(drive, folder_path, folder_description)
        else:
            self._file_system.make_dirs(folder_path)
            self._write_only_store.add_folder(folder_path, folder_description)

    def _write_folder(self, drive, folder_path, folder_description):
        full_folder_path = '%s/%s' % (drive, folder_path)
        self._file_system.make_dirs(full_folder_path)
        if drive == self._config[K_BASE_PATH]:
            self._write_only_store.add_folder(folder_path, folder_description)
            return

        self._write_only_store.add_external_folder(drive, folder_path, folder_description)
        if folder_path in self._read_only_store.folders and not self._file_system.is_folder(folder_path):
            self._write_only_store.remove_folder(folder_path)

    def remove_deleted_files(self):
        files_to_delete = self._read_only_store.list_missing_files(self._db.files)

        for file_path, description in files_to_delete.items():
            self._write_only_store.remove_file(file_path)

            drives = {drive: True for drive in self._external_drives_repository.connected_drives()}
            if is_system_path(description):
                drives[self._config[K_BASE_SYSTEM_PATH]] = False
            else:
                drives[self._config[K_BASE_PATH]] = False

            for drive, is_external in drives.items():
                if is_external:
                    self._write_only_store.remove_external_file(drive, file_path)
                else:
                    self._write_only_store.remove_file(file_path)

                full_file_path = '%s/%s' % (drive, file_path)
                if not self._file_system.is_file(full_file_path):
                    continue
                self._file_system.unlink(full_file_path)

        if len(files_to_delete) > 0:
            self._logger.print()


def is_system_path(description: Dict[str, str]) -> bool:
    return 'path' in description and description['path'] == 'system'


class WrongDatabaseOptions(Exception):
    pass

