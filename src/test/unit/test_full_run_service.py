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

import unittest
from unittest.mock import Mock

from downloader.config import default_config
from downloader.constants import EXIT_ERROR_FAILED_DBS, EXIT_ERROR_STORE_NOT_SAVED, EXIT_ERROR_NO_CERTS, \
    EXIT_ERROR_STORE_NOT_LOADED, FILE_downloader_run_signal
from downloader.error import DownloaderError
from downloader.job_system import JobFailPolicy
from test.fake_local_repository import LocalRepository
from test.fake_external_drives_repository import ExternalDrivesRepositoryStub
from test.fake_file_system_factory import FileSystemFactory
from test.fake_importer_implicit_inputs import FileSystemState, NetworkState
from test.fake_os_utils import SpyOsUtils
from test.fake_full_run_service import FullRunService
from test.objects import raw_db_empty_descr, raw_db_empty_with_linux_descr, raw_db_wrong_descr, db_empty, db_test, raw_db_descr, file_a_descr


class TestFullRunService(unittest.TestCase):
    def test_full_run___no_databases___returns_0(self):
        exit_code = FullRunService.with_no_dbs().full_run()
        self.assertEqual(exit_code, 0)

    def test_full_run___empty_databases___returns_0(self):
        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_descr()).full_run()
        self.assertEqual(exit_code, 0)

    def test_full_run___database_with_wrong_id___returns_exit_code_error_failed_dbs(self):
        exit_code = FullRunService.with_single_db(db_empty, raw_db_wrong_descr()).full_run()
        self.assertEqual(exit_code, EXIT_ERROR_FAILED_DBS)

    def test_full_run___database_not_fetched___returns_exit_code_error_failed_dbs(self):
        exit_code = FullRunService.with_single_empty_db().full_run()
        self.assertEqual(exit_code, EXIT_ERROR_FAILED_DBS)

    def test_full_run___database_with_old_linux___calls_update_linux_and_returns_0(self):
        os_utils = SpyOsUtils()
        linux_updater = old_linux()

        exit_code = FullRunService.with_single_db(db_empty, raw_db_empty_with_linux_descr(), linux_updater=linux_updater, os_utils=os_utils).full_run()

        self.assertEqual(exit_code, 0)
        linux_updater.update_linux.assert_called()
        self.assertEqual(0, os_utils.calls_to_reboot)

    def test_full_run___database_with_new_linux___calls_update_linux_and_reboots(self):
        os_utils = SpyOsUtils()
        linux_updater = new_linux()

        FullRunService.with_single_db(db_empty, raw_db_empty_with_linux_descr(), linux_updater=linux_updater, os_utils=os_utils).full_run()

        self.assertEqual(1, os_utils.calls_to_reboot)

    def test_full_run___when_certificates_check_fails___returns_exit_code_error_no_certs(self):
        certificates_fix = Mock()
        certificates_fix.fix_certificates_if_needed.return_value = False
        network_state = NetworkState()
        network_state.remote_failures['https://empty'] = 99

        exit_code = FullRunService\
            .with_single_db(db_empty, raw_db_empty_with_linux_descr(), certificates_fix=certificates_fix, network_state=network_state)\
            .full_run()

        self.assertEqual(EXIT_ERROR_NO_CERTS, exit_code)

    def test_full_run___when_network_fails_certificates_check_passes_and_networks_gets_fixed___returns_0(self):
        network_state = NetworkState()
        network_state.remote_failures['https://empty'] = default_config()['downloader_retries'] + 2
        network_state.remote_files['https://empty'] = {'unzipped_json': raw_db_empty_with_linux_descr()}

        exit_code = FullRunService\
            .with_single_db(db_empty, raw_db_empty_with_linux_descr(), network_state=network_state)\
            .full_run()

        self.assertEqual(0, exit_code)

    def test_full_run___when_local_store_doesnt_load___returns_error_code_store_not_loaded(self):
        def raise_downloader_error():
            raise DownloaderError('boom!')
        local_repository = LocalRepository()
        local_repository.load_store = raise_downloader_error

        exit_code = FullRunService\
            .with_single_db(db_empty, raw_db_empty_with_linux_descr(), local_repository=local_repository, job_fail_policy=JobFailPolicy.FAULT_TOLERANT)\
            .full_run()

        self.assertEqual(EXIT_ERROR_STORE_NOT_LOADED, exit_code)

    def test_full_run___test_database_but_failing_folders_on_fs___returns_exit_code_error_store_not_saved(self):
        db_id, db_descr, file_system_factory = test_database_setup()
        file_system_factory.set_create_folders_will_error()
        exit_code = FullRunService.with_single_db(db_id, db_descr, file_system_factory=file_system_factory).full_run()
        self.assertEqual(EXIT_ERROR_STORE_NOT_SAVED, exit_code)

    def test_full_run___test_database_with_no_fs_problems___returns_exit_code_0(self):
        db_id, db_descr, file_system_factory = test_database_setup()
        exit_code = FullRunService.with_single_db(db_id, db_descr, file_system_factory=file_system_factory).full_run()
        self.assertEqual(0, exit_code)

    def test_full_run___when_file_signal_run_is_there___removes_it(self):
        fs = FileSystemFactory(FileSystemState(files={FILE_downloader_run_signal: file_a_descr()}))
        self.assertTrue(fs.create_for_system_scope().is_file(FILE_downloader_run_signal))
        FullRunService.with_no_dbs(file_system_factory=fs).full_run()
        self.assertFalse(fs.create_for_system_scope().is_file(FILE_downloader_run_signal))

    def test_print_drives___when_there_are_external_drives___returns_0(self):
        self.assertEqual(0, FullRunService(external_drives_repository=ExternalDrivesRepositoryStub(['/wtf'])).print_drives())


def test_database_setup():
    db_id = db_test
    db_descr = raw_db_descr(db_id, folders={'test_folder': {}})
    config = FullRunService.single_db_config(db_id)
    return db_id, db_descr, FileSystemFactory(config=config, state=FileSystemState(config=config, files={db_id: {'unzipped_json': db_descr}}))


def new_linux():
    linux_updater = Mock()
    linux_updater.needs_reboot.return_value = True
    return linux_updater


def old_linux():
    linux_updater = Mock()
    linux_updater.needs_reboot.return_value = False
    return linux_updater
