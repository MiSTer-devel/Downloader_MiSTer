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

import datetime
import json
import sys
import time
from pathlib import Path

from downloader.base_path_relocator import BasePathRelocator
from downloader.certificates_fix import CertificatesFix
from downloader.config import Config
from downloader.db_utils import DbSectionPackage, sorted_db_sections
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.linux_updater import LinuxUpdater
from downloader.local_repository import LocalRepository
from downloader.logger import FilelogManager, Logger, ConfigLogManager
from downloader.online_importer import OnlineImporter, InstallationBox
from downloader.os_utils import OsUtils
from downloader.other import format_files_message, format_folders_message, format_zips_message
from downloader.reboot_calculator import RebootCalculator
from downloader.waiter import Waiter


class FullRunService:
    def __init__(self, config: Config, logger: Logger, filelog_manager: FilelogManager, printlog_manager: ConfigLogManager, local_repository: LocalRepository, online_importer: OnlineImporter, linux_updater: LinuxUpdater, reboot_calculator: RebootCalculator, base_path_relocator: BasePathRelocator, certificates_fix: CertificatesFix, external_drives_repository: ExternalDrivesRepository, os_utils: OsUtils, waiter: Waiter):
        self._waiter = waiter
        self._os_utils = os_utils
        self._external_drives_repository = external_drives_repository
        self._certificates_fix = certificates_fix
        self._base_path_relocator = base_path_relocator
        self._reboot_calculator = reboot_calculator
        self._linux_updater = linux_updater
        self._online_importer = online_importer
        self._local_repository = local_repository
        self._logger = logger
        self._filelog_manager = filelog_manager
        self._printlog_manager = printlog_manager
        self._config = config

    def configure_components(self):
        self._printlog_manager.configure(self._config)
        self._filelog_manager.set_local_repository(self._local_repository)
        self._logger.debug('config: ' + json.dumps(self._config, default=lambda o: str(o) if isinstance(o, Path) else o.__dict__, indent=4))

    def print_drives(self):
        self._logger.bench('Print Drives start.')

        self._local_repository.set_logfile_path('/tmp/print_drives.log')
        self._logger.print('\nPrinting External Drives:')
        for drive in self._external_drives_repository.connected_drives():
            self._logger.print(drive)

        self._logger.bench('Print Drives done.')
        return 0

    def full_run(self):
        self._logger.bench('Full Run start.')
        result = self._full_run_impl()
        self._logger.bench('Full Run done.')

        if not self._config['is_pc_launcher'] and self._needs_reboot():
            self._logger.print()
            self._logger.print("Rebooting in 10 seconds...")
            sys.stdout.flush()
            self._waiter.sleep(2)
            self._filelog_manager.finalize()
            sys.stdout.flush()
            self._waiter.sleep(4)
            self._os_utils.sync()
            self._waiter.sleep(4)
            self._os_utils.sync()
            self._waiter.sleep(30)
            self._os_utils.reboot()

        return result

    def _full_run_impl(self):
        self._logger.print('START!')
        self._logger.print()
        self._logger.debug('Linux Version: %s' % self._linux_updater.get_current_linux_version())

        self._local_repository.ensure_base_paths()

        if not self._check_certificates():
            self._logger.print("ERROR: Couldn't load certificates.")
            self._logger.print()
            self._logger.print("Please, reboot your system and try again.")
            self._waiter.sleep(50)
            return 1

        local_store = self._local_repository.load_store()

        db_pkgs = [DbSectionPackage(db_id, section, local_store.store_by_id(db_id)) for db_id, section in sorted_db_sections(self._config)]
        #db_pkgs = [db_pkg for db_pkg in db_pkgs  if db_pkg.db_id == 'distribution_mister']

        for relocation_package in self._base_path_relocator.relocating_base_paths(db_pkgs):
            self._base_path_relocator.relocate_non_system_files(relocation_package)
            self._local_repository.save_store(local_store)

        full_resync = not self._local_repository.has_last_successful_run()
        self._online_importer.set_local_store(local_store)
        self._online_importer.download_dbs_contents(db_pkgs, full_resync)

        self._local_repository.save_store(local_store)

        install_box = self._online_importer.box()
        self._display_summary(install_box, self._config['start_time'])

        if self._config['update_linux']:
            self._linux_updater.update_linux(self._online_importer.correctly_downloaded_dbs())

        if self._config['fail_on_file_error']:
            failure_count = len(self._online_importer.files_that_failed()) + len(self._online_importer.folders_that_failed()) + len(self._online_importer.zips_that_failed())
            if failure_count > 0:
                self._logger.debug('Length of files_that_failed: %d' % len(self._online_importer.files_that_failed()))
                self._logger.debug('Length of folders_that_failed: %d' % len(self._online_importer.folders_that_failed()))
                self._logger.debug('Length of zips_that_failed: %d' % len(self._online_importer.zips_that_failed()))
                self._logger.debug('Length of failed_dbs: %d' % len(install_box.failed_dbs()))
                return 1

        if len(install_box.failed_dbs()) > 0:
            self._logger.debug('Length of failed_dbs: %d' % len(install_box.failed_dbs()))
            return 1

        return 0

    def _check_certificates(self):
        for i in range(3):
            if i != 0:
                self._logger.debug()
                self._logger.debug("Attempting again in 10 seconds...")
                self._waiter.sleep(10)
                self._logger.debug()

            if self._certificates_fix.fix_certificates_if_needed():
                return True

        return False

    def _display_summary(self, box: InstallationBox, start_time):
        run_time = str(datetime.timedelta(seconds=time.time() - start_time))[0:-4]

        self._logger.print()
        self._logger.print('===========================')
        self._logger.print(f'Downloader 2.0 ({self._config["commit"][0:3]}) by theypsilon. Run time: {run_time}s at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self._logger.debug('Commit: %s', self._config["commit"])
        self._logger.print(f'Log: {self._local_repository.logfile_path}')
        if len(box.unused_filter_tags()) > 0:
            self._logger.print()
            self._logger.print("Unused filter terms:")
            self._logger.print(format_files_message(box.unused_filter_tags()) + f" (Did you misspell {'it' if len(box.unused_filter_tags()) == 1 else 'them'}?)")

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
                self._logger.print(' •%s: %s' % (db_id, ', '.join(new_files_not_installed[db_id])))
            self._logger.print()
            self._logger.print(' * Delete the file that you wish to upgrade from the previous list, and run this again.')
        if len(box.full_partitions()) > 0:
            full_partitions = [p for p, s in box.full_partitions().items()]
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

    def _needs_reboot(self):
        return self._reboot_calculator.calc_needs_reboot(self._linux_updater.needs_reboot(), self._online_importer.needs_reboot())
