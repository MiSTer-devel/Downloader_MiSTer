# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import datetime
import sys
import time
from typing import Optional

from downloader.certificates_fix import CertificatesFix
from downloader.config import Config, FileChecking
from downloader.constants import DOWNLOADER_VERSION, EXIT_ERROR_NO_CERTS, EXIT_ERROR_STORE_NOT_SAVED, EXIT_ERROR_FAILED_FILES, \
    EXIT_ERROR_FAILED_DBS, EXIT_ERROR_STORE_NOT_LOADED, REBOOT_WAIT_TIME_AFTER_LINUX_UPDATE, \
    REBOOT_WAIT_TIME_STANDARD, FILE_CHECKING_SPACE_CHECK_TOLERANCE, MEDIA_FAT, EXIT_ERROR_NETWORK_PROBLEMS, \
    FILE_downloader_storage_backup_pext, EXIT_ERROR_WRONG_SETUP
from downloader.db_utils import DbSectionPackage, sorted_db_sections
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.linux_updater import LinuxUpdater
from downloader.local_repository import LocalRepository
from downloader.logger import FilelogManager, Logger, ConfigLogManager
from downloader.online_importer import OnlineImporter, InstallationBox, NetworkProblems
from downloader.os_utils import OsUtils
from downloader.other import format_files_message, format_folders_message, format_zips_message, remove_run_signal, screen_columns
from downloader.reboot_calculator import RebootCalculator
from downloader.waiter import Waiter
from downloader.update_output import UpdateOutput


class FullRunService:
    def __init__(self, config: Config, logger: Logger, filelog_manager: FilelogManager, printlog_manager: ConfigLogManager, local_repository: LocalRepository, online_importer: OnlineImporter, linux_updater: LinuxUpdater, reboot_calculator: RebootCalculator, certificates_fix: CertificatesFix, external_drives_repository: ExternalDrivesRepository, os_utils: OsUtils, waiter: Waiter, file_system: FileSystem, update_output: UpdateOutput) -> None:
        self._waiter = waiter
        self._os_utils = os_utils
        self._external_drives_repository = external_drives_repository
        self._certificates_fix = certificates_fix
        self._reboot_calculator = reboot_calculator
        self._linux_updater = linux_updater
        self._online_importer = online_importer
        self._local_repository = local_repository
        self._logger = logger
        self._filelog_manager = filelog_manager
        self._printlog_manager = printlog_manager
        self._config = config
        self._file_system = file_system
        self._update_output = update_output
        self._file_checking_mode_resolver = FileCheckingModeResolver(local_repository, file_system, logger)
        self._final_reporter = FinalReporter(local_repository, config, logger, waiter, self._update_output)

    def configure_components(self) -> None:
        self._logger.bench('FullRunService configure_components start.')
        self._printlog_manager.configure(self._config)
        self._filelog_manager.set_local_repository(self._local_repository)
        self._logger.bench('FullRunService configure_components done.')

    def print_drives(self) -> int:
        self._logger.bench('FullRunService Print Drives start.')

        self._local_repository.set_logfile_path('/tmp/print_drives.log')
        self._logger.print('\nPrinting External Drives:')
        for drive in self._external_drives_repository.connected_drives():
            self._logger.print(drive)

        self._logger.bench('FullRunService Print Drives done.')
        self._remove_run_signal()

        return 0

    def full_run(self):
        return self._run(None)

    def run_only(self, db_ids: list[str]) -> int:
        return self._run(set(db_ids))

    def _run(self, filter_db_ids: Optional[set[str]]) -> int:
        self._update_output.run_started(DOWNLOADER_VERSION, self._config['commit'])
        self._logger.bench('FullRunService Full Run start.')
        result = self._run_impl(filter_db_ids)
        self._logger.bench('FullRunService Full Run done.')
        self._remove_run_signal()

        needs_reboot = False if self._config['is_pc_launcher'] else self._needs_reboot()
        if needs_reboot:
            self._update_output.reboot_required('linux' if self._linux_updater.needs_reboot() else 'standard')

        self._update_output.run_finished(result)

        if needs_reboot:
            self._logger.print()
            if self._linux_updater.needs_reboot():
                self._logger.print(f"Rebooting in {REBOOT_WAIT_TIME_AFTER_LINUX_UPDATE} seconds. Please do not turn off your device!")
            else:
                self._logger.print(f"Rebooting in {REBOOT_WAIT_TIME_STANDARD} seconds...")
            sys.stdout.flush()
            self._filelog_manager.finalize()
            sys.stdout.flush()
            self._os_utils.sync()
            if self._linux_updater.needs_reboot():
                self._waiter.sleep(1)
                self._os_utils.sync()
                self._waiter.sleep(REBOOT_WAIT_TIME_AFTER_LINUX_UPDATE - 1)
            else:
                self._waiter.sleep(REBOOT_WAIT_TIME_STANDARD)
            self._os_utils.reboot()

        return result

    def _run_impl(self, filter_db_ids: Optional[set[str]] = None):
        self._logger.debug('Linux Version: %s' % self._linux_updater.get_current_linux_version())

        self._local_repository.ensure_base_paths()

        file_checking_opt = self._config['file_checking']
        new_file_checking = self._file_checking_mode_resolver.calc_file_checking_changes(file_checking_opt)
        if new_file_checking is not None:
            self._logger.debug(f'File checking changed from "{file_checking_opt}" to "{new_file_checking}".')
            self._config['file_checking'] = new_file_checking

        db_sections = sorted_db_sections(self._config)
        if filter_db_ids is not None:
            configured_db_ids = set(db_id for db_id, _ in db_sections)
            invalid_db_ids = sorted(filter_db_ids - configured_db_ids)
            if len(filter_db_ids) == 0 or len(invalid_db_ids) > 0:
                if len(filter_db_ids) == 0:
                    self._update_output.error('run_only_empty_db_ids', 'No database ids were provided.')
                else:
                    self._update_output.error('run_only_invalid_db_ids', 'Invalid database ids: ' + ', '.join(invalid_db_ids))
                return EXIT_ERROR_WRONG_SETUP

            db_sections = [(db_id, section) for db_id, section in db_sections if db_id in filter_db_ids]

        db_pkgs = [DbSectionPackage(db_id, section) for db_id, section in db_sections]
        #db_pkgs = [db_pkg for db_pkg in db_pkgs  if db_pkg.db_id == 'distribution_mister']

        install_box, download_dbs_err = self._online_importer.download_dbs_contents(db_pkgs)
        if download_dbs_err is not None:
            self._logger.debug(download_dbs_err)
            if isinstance(download_dbs_err, NetworkProblems):
                if not self._check_certificates():
                    self._final_reporter.display_no_certs_msg()
                    return EXIT_ERROR_NO_CERTS

                self._update_output.warning('network_retry', 'Retrying all connections...')
                install_box, download_dbs_err = self._online_importer.download_dbs_contents(db_pkgs)

            if isinstance(download_dbs_err, NetworkProblems):
                self._final_reporter.display_network_problems_msg()
                return EXIT_ERROR_NETWORK_PROBLEMS
            elif download_dbs_err is not None:
                self._final_reporter.display_no_store_msg()
                return EXIT_ERROR_STORE_NOT_LOADED

        if len(install_box.old_pext_paths()) > 0:
            self._local_repository.backup_local_store_for_pext_error()

        save_store_err = self._local_repository.save_store(install_box.local_store())

        if file_checking_opt == FileChecking.BALANCED and len(install_box.failed_files()) > 0:
            self._local_repository.remove_free_spaces()
        elif file_checking_opt != FileChecking.FASTEST:
            self._local_repository.save_free_spaces(self._file_system.free_spaces())

        self._final_reporter.display_end_summary(install_box)

        if save_store_err is not None:
            self._update_output.error('store_save', 'Store could not be saved because of a File System Error!')
            return EXIT_ERROR_STORE_NOT_SAVED

        if self._config['update_linux']:
            self._linux_updater.update_linux(install_box.installed_dbs())

        if self._config['fail_on_file_error']:
            failure_count = len(install_box.failed_files()) + len(install_box.failed_folders()) + len(install_box.failed_zips())
            if failure_count > 0:
                self._final_reporter.display_file_error_failures(install_box)
                return EXIT_ERROR_FAILED_FILES

        if len(install_box.failed_dbs()) > 0:
            self._logger.debug('Length of failed_dbs: %d' % len(install_box.failed_dbs()))
            return EXIT_ERROR_FAILED_DBS

        return 0

    def _check_certificates(self) -> bool:
        for i in range(3):
            if i != 0:
                self._logger.debug()
                self._logger.debug("Attempting again in 10 seconds...")
                self._waiter.sleep(10)
                self._logger.debug()

            if self._certificates_fix.fix_certificates_if_needed():
                return True

        return False

    def _needs_reboot(self):
        return self._reboot_calculator.calc_needs_reboot(self._linux_updater.needs_reboot(), self._online_importer.needs_reboot())

    def _remove_run_signal(self) -> None:
        remove_run_signal(self._file_system, self._logger)

class FileCheckingModeResolver:
    def __init__(self, local_repository: LocalRepository, file_system: FileSystem, logger: Logger) -> None:
        self._local_repository = local_repository
        self._file_system = file_system
        self._logger = logger

    def calc_file_checking_changes(self, file_checking: FileChecking) -> Optional[FileChecking]:
        if not self._local_repository.has_last_successful_run() and self._local_repository.has_store():
            self._logger.print('WARNING: Deprecated "force checking" through .last_successful_run removal in Downloader 2.3')
            self._logger.print('WARNING: Set the option file_checking = 3 in downloader.ini instead.')
            self._logger.print('WARNING: It will be removed in a future version.')
            return FileChecking.VERIFY_INTEGRITY

        if file_checking == FileChecking.BALANCED:
            if self._local_repository.has_store_for_pext_error(): return FileChecking.EXHAUSTIVE  # @TODO: This is for the pext bug. Remove it after a while

            prev_free_spaces = self._local_repository.load_previous_free_spaces()
            actual_free_spaces = self._file_system.free_spaces()
            if MEDIA_FAT not in prev_free_spaces or MEDIA_FAT not in actual_free_spaces:
                return FileChecking.EXHAUSTIVE

            for partition, cur_free_space in actual_free_spaces.items():
                if partition not in prev_free_spaces:
                    continue

                if cur_free_space > (prev_free_spaces[partition] + FILE_CHECKING_SPACE_CHECK_TOLERANCE):
                    return FileChecking.EXHAUSTIVE  # Free space as increased substantially... Did the user remove installed files? Assume yes.

            return FileChecking.FASTEST

        return None


class FinalReporter:
    def __init__(self, local_repository: LocalRepository, config: Config, logger: Logger, waiter: Waiter, update_output: UpdateOutput) -> None:
        self._local_repository = local_repository
        self._config = config
        self._logger = logger
        self._waiter = waiter
        self._update_output = update_output

    def display_end_summary(self, box: InstallationBox) -> None:
        run_time = str(datetime.timedelta(seconds=time.monotonic() - self._config['start_time']))[2:-4]

        for db_id in box.failed_dbs():
            self._update_output.database_failed(db_id)
        for db_id, zip_id in box.failed_zips():
            self._update_output.zip_failed(db_id, zip_id)
        for folder in box.failed_folders():
            self._update_output.folder_failed(folder)

        self._logger.print()
        self._logger.print('=' * screen_columns())
        self._logger.print(f'Downloader {DOWNLOADER_VERSION} ({self._config["commit"][0:3]}) by theypsilon. Run time: {run_time}s at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self._logger.debug('Commit: %s', self._config["commit"])
        self._logger.print(f'Log: {self._local_repository.logfile_path}')
        if len(box.skipped_dbs()) == 0 and len(box.unused_filter_tags()) > 0:
            self._logger.print()
            self._logger.print("Unused filter terms:")
            self._logger.print(format_files_message(box.unused_filter_tags()) + f" (Did you misspell {'it' if len(box.unused_filter_tags()) == 1 else 'them'}?)")

        if self._config['file_checking'] == FileChecking.VERIFY_INTEGRITY:
            verified_integrity_files_amount = len(box.verified_integrity_files())
            failed_verification_amount = len(box.failed_verification_files())

            self._logger.print()
            self._logger.print(f'Verify Integrity report:')
            if verified_integrity_files_amount > 0:
                self._logger.print(f'  - Verified {verified_integrity_files_amount} files.' + (' All files were verified.' if failed_verification_amount == 0 else ''))
            if failed_verification_amount > 0:
                self._logger.print(f'  - Verification failed for {failed_verification_amount} files; they were reinstalled.')
            if verified_integrity_files_amount == 0 and failed_verification_amount == 0:
                self._logger.print(f'  - No files to check.')

        if len(box.updated_dbs()) > 0 and len(box.installed_dbs()) > 1:
            self._logger.print()
            self._logger.print('Updates found in the following databases:')
            self._logger.print(' '.join([f'[{db_id}]' for db_id in box.updated_dbs()]))

        self._logger.print()
        self._logger.print('Installed:')
        self._logger.print(format_files_message(box.installed_file_names()))
        self._logger.print()
        self._logger.print('Errors:')
        self._logger.print(format_files_message(box.failed_files() + [f'[{db}]' for db in box.failed_dbs()]))
        if len(box.failed_folders()) > 0:
            self._logger.print(format_folders_message(box.failed_folders()))
        if len(box.failed_zips()) > 0:
            self._logger.print(format_zips_message([f'{db_id}:{zip_id}' for db_id, zip_id in box.failed_zips()]))
        if len(box.skipped_updated_files()) > 0:
            new_files_not_installed = box.skipped_updated_files()
            self._logger.print()
            self._logger.print('Following new versions were not installed:')
            for db_id in new_files_not_installed:
                for path in new_files_not_installed[db_id]:
                    self._update_output.not_overwritten(db_id, path)
                self._logger.print(' •%s: %s' % (db_id, ', '.join(new_files_not_installed[db_id])))
            self._logger.print()
            self._logger.print(' * Delete the file that you wish to upgrade from the previous list, and run this again.')
        if len(box.full_partitions()) > 0:
            full_partitions = [p for p, s in box.full_partitions().items()]
            for partition, bytes_needed in box.full_partitions().items():
                self._update_output.full_partition(partition, bytes_needed)
            has_system = any(partition == self._config['base_system_path'] for partition in full_partitions)
            has_external = any(partition != self._config['base_system_path'] for partition in full_partitions)
            self._logger.print()
            self._logger.print("################################################################################")
            self._logger.print("################################## IMPORTANT! ##################################")
            self._logger.print("################################################################################")
            self._logger.print()
            self._logger.print("You DON'T have enough free space to run Downloader!")
            for partition in full_partitions: self._logger.print(f' - {partition} is FULL')
            self._logger.print()
            if has_system: self._logger.print(f"Minimum required space for {self._config['base_system_path']} is {self._config['minimum_system_free_space_mb']}MB.")
            if has_external: self._logger.print(f"Minimum required space for external storage is {self._config['minimum_external_free_space_mb']}MB.")
            self._logger.print('Free some space and try again. [Waiting 10 seconds...]')
            self._waiter.sleep(10)

        self._logger.print()
        old_pext_paths = box.old_pext_paths()
        if old_pext_paths:
            self._logger.print(
                f'WARNING! There was some buggy path in the process like "{list(old_pext_paths)[0]}".\n\n'
                f'         I need YOUR HELP to fix this!!! Please, send me the following file\n'
                f'           "{FILE_downloader_storage_backup_pext}"\n'
                f'         to my email: theypsilon@gmail.com\n\n'
                f'         This is not a breaking error. All files are safe.\n'
                f'         You may run Downloader again without problems. Thank you!\n'
            )
            self._waiter.sleep(5)
            self._logger.debug('Old pext paths: ' + ', '.join(old_pext_paths))

    def display_no_certs_msg(self) -> None:
        self._update_output.error('no_certs', "Couldn't load certificates.")
        self._logger.print()
        self._logger.print("Please, reboot your system and try again.")
        self._waiter.sleep(50)

    def display_network_problems_msg(self) -> None:
        self._update_output.error('network', "Couldn't connect to the servers.")
        self._logger.print()
        self._logger.print("Please, reboot your system and try again.")
        self._logger.print()
        self._logger.print("If your region suffers from restricted connectivity, consider:")
        self._logger.print(" - Using a HTTP Proxy.")
        self._logger.print(" - Using the PC Launcher through a VPN.")
        self._logger.print()
        self._logger.print("Check the README at https://github.com/MiSTer-devel/Downloader_MiSTer for more information.")
        self._waiter.sleep(50)

    def display_no_store_msg(self) -> None:
        self._update_output.error('store_load', 'Store could not be loaded because of a File System Error!')
        self._logger.print()
        self._logger.print("Please, reboot your system and try again.")

    def display_file_error_failures(self, box: InstallationBox) -> None:
        self._update_output.error('file_failures', 'Variable FAIL_ON_FILE_ERROR was set to true, and found the following errors.')
        self._logger.print()
        self._logger.print('Files that failed: %d' % len(box.failed_files()))
        self._logger.print('Folders that failed: %d' % len(box.failed_folders()))
        self._logger.print('Zips that failed: %d' % len(box.failed_zips()))
        self._logger.print('Databases that failed: %d' % len(box.failed_dbs()))
