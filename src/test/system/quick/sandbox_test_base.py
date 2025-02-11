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
import unittest
import shutil
import os
import json
from pathlib import Path, PurePosixPath

from downloader.config_reader import ConfigReader
from downloader.constants import FILE_downloader_storage_json
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.full_run_service_factory import FullRunServiceFactory
from downloader.logger import PrintLogger
from downloader.other import UnreachableException
from test.fake_file_system_factory import make_production_filesystem_factory
from test.fake_logger import SpyLoggerDecorator
from test.objects import debug_env, default_env
from test.fake_logger import NoLogger
from test.fake_store_migrator import StoreMigrator
from downloader.file_system import hash_file, is_windows
from downloader.main import execute_full_run
from downloader.store_migrator import make_new_local_store


tmp_delme_sandbox = '/tmp/delme_sandbox/'
tmp_default_base_path = '/tmp/default_base_path'


class SandboxTestBase(unittest.TestCase):
    def assertExecutesCorrectly(self, ini_path, expected=None, external_drives_repository_factory=None):
        external_drives_repository_factory = external_drives_repository_factory or ExternalDrivesRepositoryFactory()
        self.maxDiff = None
        logger_print = PrintLogger()
        logger_spy = SpyLoggerDecorator(logger_print)
        exit_code = self.run_execute_full_run(ini_path, external_drives_repository_factory, logger_spy, logger_print)
        self.assertEqual(exit_code, 0)

        if expected is None:
            return

        transform_windows_paths_from_expected(expected)

        config = ConfigReader(NoLogger(), debug_env()).read_config(ini_path)
        self.file_system = make_production_filesystem_factory(config).create_for_system_scope()
        counter = 0
        if 'local_store' in expected:
            counter += 1
            with self.subTestAdapter('local_store'):
                actual_store = load_json(os.path.join(config['base_system_path'], FILE_downloader_storage_json))
                self.assertEqual(expected['local_store'], actual_store)

        if 'files' in expected:
            counter += 1
            with self.subTestAdapter('files'):
                self.assertEqual(expected['files'], self.find_all_files(config['base_path']))

        if 'files_count' in expected:
            counter += 1
            with self.subTestAdapter('files_count'):
                self.assertEqual(expected['files_count'], len(self.find_all_files(config['base_path'])))

        if 'system_files' in expected:
            counter += 1
            with self.subTestAdapter('system_files'):
                self.assertEqual(expected['system_files'], self.find_all_files(config['base_system_path']))

        if 'system_files_count' in expected:
            counter += 1
            with self.subTestAdapter('system_files_count'):
                self.assertEqual(expected['system_files_count'], len(self.find_all_files(config['base_path'])))

        if 'folders' in expected:
            counter += 1
            with self.subTestAdapter('folders'):
                self.assertEqual(sorted(list(expected['folders'])), self.find_all_folders(config['base_path']))

        if 'system_folders' in expected:
            counter += 1
            with self.subTestAdapter('system_folders'):
                self.assertEqual(sorted(list(expected['system_folders'])), self.find_all_folders(config['base_system_path']))

        if 'installed_log' in expected:
            counter += 1
            with self.subTestAdapter('installed_log'):
                installed_next = False
                installed_entries = None
                for entry in logger_spy.printCalls:
                    if installed_next:
                        installed_next = False
                        installed_entries = {entry.strip() for entry in entry[0].split(',')}
                    else:
                        if entry and entry[0].startswith('Installed:'):
                            installed_next = True

            self.assertEqual({Path(file).name for file in expected['installed_log']}, installed_entries)

        self.assertEqual(len(expected), counter)

    def subTestAdapter(self, message):
        #return contextlib.suppress()
        return self.subTest(message)

    def run_execute_full_run(self, ini_path, external_drives_repository_factory, logger, print_mgr, argv=None):
        env = default_env()
        env['DOWNLOADER_LAUNCHER_PATH'] = str(Path(ini_path).with_suffix('.sh'))
        env['UPDATE_LINUX'] = 'false'
        env['ALLOW_REBOOT'] = '0'
        env['COMMIT'] = 'quick system test'
        env['DEBUG'] = 'true'
        env['LOGLEVEL'] = '' # info, http
        env['FAIL_ON_FILE_ERROR'] = 'true'
        env['CURL_SSL'] = ''
        env['DEFAULT_BASE_PATH'] = tmp_default_base_path

        config_reader = ConfigReader(logger, env)
        factory = FullRunServiceFactory(logger, NoLogger(), print_mgr, external_drives_repository_factory=external_drives_repository_factory)
        return execute_full_run(factory, config_reader, argv or [])

    def find_all_files(self, directory):
        return [(file.replace('\\', '/'), md5) for file, md5 in sorted(self._scan_files(directory), key=lambda t: t[0].lower())]

    def _scan_files(self, directory):
        for entry in os.scandir(directory):
            if entry.is_dir(follow_symlinks=False):
                yield from self._scan_files(entry.path)
            else:
                yield entry.path, hash_file(entry.path)

    def find_all_folders(self, directory):
        if not directory.endswith('/'):
            directory = directory + '/'
        return [folder.replace('\\', '/') for folder in sorted(self._scan_folders(directory, directory), key=str.casefold)]

    def _scan_folders(self, directory, base):
        for entry in os.scandir(directory):
            if entry.is_dir(follow_symlinks=False):
                yield from self._scan_folders(entry.path, base)
                yield entry.path[len(base):]


def local_store_files(tuples):
    if not len(tuples):
        raise UnreachableException("Forgot adding some tuples!")
    if len(tuples[0]) == 2:
        tuples = [tuple([store_id, files, {}]) for store_id, files in tuples]
    if len(tuples[0]) != 3:
        raise UnreachableException("This is not meant to be used like this!")

    store = make_new_local_store(StoreMigrator())
    for store_id, files, folders in tuples:
        store['dbs'][store_id] = {
            'base_path': tmp_delme_sandbox[0:-1],
            'folders': {(f if f[0] != '|' else f[1:]): d for f, d in folders.items()},
            'files': fix_relative_files(files),
            'offline_databases_imported': [],
            'zips': {}
        }
    return store


def fix_relative_files(files):
    return {(file_path if file_path[0] != '|' else file_path[1:]): file_description for file_path, file_description in files.items()}


def cleanup(ini_path):
    env = debug_env()
    env['DEFAULT_BASE_PATH'] = tmp_default_base_path
    config = ConfigReader(NoLogger(), env).read_config(ini_path)
    delete_folder(config['base_path'])
    delete_folder(config['base_system_path'])
    create_folder(config['base_path'])
    create_folder(config['base_system_path'])


def create_folder(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def delete_folder(path):
    shutil.rmtree(path, ignore_errors=True)


def hashes(base_path, files):
    files = fix_relative_files(files)
    return sorted([(base_path + f, files[f]['hash']) for f in files])


def load_json(file_path):
    with open(file_path, "r") as f:
        return json.loads(f.read())


def transform_windows_paths_from_expected(expected):
    if not is_windows:
        return

    transform_windows_paths_from_file_collection(expected, 'files')
    transform_windows_paths_from_file_collection(expected, 'system_files')
    transform_windows_paths_from_folder_collection(expected, 'folders')
    transform_windows_paths_from_folder_collection(expected, 'system_folders')


def transform_windows_paths_from_file_collection(expected, field):
    if field not in expected:
        return
    expected[field] = [(str(PurePosixPath(file)).replace('\\', '/'), md5) for file, md5 in expected[field]]


def transform_windows_paths_from_folder_collection(expected, field):
    if field not in expected:
        return
    expected[field] = [str(PurePosixPath(folder)).replace('\\', '/') for folder in expected[field]]
