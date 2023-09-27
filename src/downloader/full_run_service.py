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

import datetime
import sys
import time

from downloader.constants import K_DATABASES, K_UPDATE_LINUX, \
    K_FAIL_ON_FILE_ERROR, K_COMMIT, K_START_TIME, K_IS_PC_LAUNCHER, K_MINIMUM_SYSTEM_FREE_SPACE_MB, K_BASE_SYSTEM_PATH, K_MINIMUM_EXTERNAL_FREE_SPACE_MB
from downloader.importer_command import ImporterCommandFactory
from downloader.job_system import JobSystem
from downloader.jobs.download_db_job import DownloadDbJob
from downloader.jobs.worker_context import DownloaderWorkerContext
from downloader.jobs.workers_factory import DownloaderWorkersFactory
from downloader.other import format_files_message, format_folders_message, format_zips_message


class FullRunService:
    def __init__(self, config, logger, local_repository, db_gateway, offline_importer, online_importer, linux_updater, reboot_calculator, base_path_relocator, certificates_fix, external_drives_repository, os_utils, waiter, importer_command_factory: ImporterCommandFactory, job_system: JobSystem, workers_factory: DownloaderWorkersFactory):
        self._importer_command_factory = importer_command_factory
        self._waiter = waiter
        self._os_utils = os_utils
        self._external_drives_repository = external_drives_repository
        self._certificates_fix = certificates_fix
        self._base_path_relocator = base_path_relocator
        self._reboot_calculator = reboot_calculator
        self._linux_updater = linux_updater
        self._online_importer = online_importer
        self._offline_importer = offline_importer
        self._db_gateway = db_gateway
        self._local_repository = local_repository
        self._logger = logger
        self._config = config
        self._job_system = job_system
        self._workers_factory = workers_factory

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

        if not self._config[K_IS_PC_LAUNCHER] and self._needs_reboot():
            self._logger.print()
            self._logger.print("Rebooting in 10 seconds...")
            sys.stdout.flush()
            self._waiter.sleep(2)
            self._logger.finalize()
            sys.stdout.flush()
            self._waiter.sleep(4)
            self._os_utils.sync()
            self._waiter.sleep(4)
            self._os_utils.sync()
            self._waiter.sleep(30)
            self._os_utils.reboot()

        return result

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

    def _full_run_impl(self):
        self._logger.debug('Linux Version: %s' % self._linux_updater.get_current_linux_version())

        if not self._check_certificates():
            self._logger.print("ERROR: Couldn't load certificates.")
            self._logger.print()
            self._logger.print("Please, reboot your system and try again.")
            self._waiter.sleep(50)
            return 1

        local_store = self._local_repository.load_store()
        full_resync = not self._local_repository.has_last_successful_run()

        self._workers_factory.prepare_workers()
        for section, ini_description in self._config[K_DATABASES].items():
            self._job_system.push_job(DownloadDbJob(
                ini_section=section,
                ini_description=ini_description,
                store=local_store.store_by_id(section),
                full_resync=full_resync
            ))

        self._job_system.accomplish_pending_jobs()
        failed_dbs = []

        # databases, failed_dbs = self._db_gateway.fetch_all(self._config[K_DATABASES])
        #
        # importer_command = self._importer_command_factory.create()
        # for db in databases:
        #     description = self._config[K_DATABASES][db.db_id]
        #     importer_command.add_db(db, local_store.store_by_id(db.db_id), description)
        #
        # for relocation_package in self._base_path_relocator.relocating_base_paths(importer_command):
        #     self._base_path_relocator.relocate_non_system_files(relocation_package)
        #     self._local_repository.save_store(local_store)
        #
        # self._offline_importer.apply_offline_databases(importer_command)
        # self._online_importer.download_dbs_contents(importer_command, full_resync)

        self._local_repository.save_store(local_store)

        self._display_summary(self._online_importer.correctly_installed_files(),
                              self._online_importer.files_that_failed() + failed_dbs,
                              self._online_importer.folders_that_failed(),
                              self._online_importer.zips_that_failed(),
                              self._online_importer.unused_filter_tags(),
                              self._online_importer.new_files_not_overwritten(),
                              self._online_importer.full_partitions(),
                              self._config[K_START_TIME])

        self._logger.print()

        # if self._config[K_UPDATE_LINUX]:
        #     self._linux_updater.update_linux(importer_command)

        if self._config[K_FAIL_ON_FILE_ERROR]:
            failure_count = len(self._online_importer.files_that_failed()) + len(self._online_importer.folders_that_failed()) + len(self._online_importer.zips_that_failed())
            if failure_count > 0:
                self._logger.debug('Length of files_that_failed: %d' % len(self._online_importer.files_that_failed()))
                self._logger.debug('Length of folders_that_failed: %d' % len(self._online_importer.folders_that_failed()))
                self._logger.debug('Length of zips_that_failed: %d' % len(self._online_importer.zips_that_failed()))
                self._logger.debug('Length of failed_dbs: %d' % len(failed_dbs))
                return 1

        if len(failed_dbs) > 0:
            self._logger.debug('Length of failed_dbs: %d' % len(failed_dbs))
            return 1

        return 0

    def _display_summary(self, installed_files, failed_files, failed_folders, failed_zips, unused_filter_tags, new_files_not_installed, full_partitions, start_time):
        run_time = str(datetime.timedelta(seconds=time.time() - start_time))[0:-4]

        self._logger.print()
        self._logger.print('===========================')
        self._logger.print(f'Downloader 1.8 ({self._config[K_COMMIT][0:3]}) by theypsilon. Run time: {run_time}s at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self._logger.debug(f'Commit: {self._config[K_COMMIT]}')
        self._logger.print(f'Log: {self._local_repository.logfile_path}')
        if len(unused_filter_tags) > 0:
            self._logger.print()
            self._logger.print("Unused filter terms:")
            if len(unused_filter_tags) != 1:
                self._logger.print(format_files_message(unused_filter_tags) + " (Did you misspell them?)")
            else:
                self._logger.print(format_files_message(unused_filter_tags) + " (Did you misspell it?)")

        self._logger.print()
        self._logger.print('Installed:')
        self._logger.print(format_files_message(installed_files))
        self._logger.print()
        self._logger.print('Errors:')
        self._logger.print(format_files_message(failed_files))
        if len(failed_folders) > 0:
            self._logger.print(format_folders_message(failed_folders))
        if len(failed_zips) > 0:
            self._logger.print(format_zips_message(failed_zips))
        if len(new_files_not_installed) > 0:
            self._logger.print()
            self._logger.print('Following new versions were not installed:')
            for db_id in new_files_not_installed:
                self._logger.print(' •%s: %s' % (db_id, ', '.join(new_files_not_installed[db_id])))
            self._logger.print()
            self._logger.print(' * Delete the file that you wish to upgrade from the previous list, and run this again.')
        if len(full_partitions) > 0:
            has_system = any(partition == self._config[K_BASE_SYSTEM_PATH] for partition in full_partitions)
            has_external = any(partition != self._config[K_BASE_SYSTEM_PATH] for partition in full_partitions)
            self._logger.print()
            self._logger.print("################################################################################")
            self._logger.print("################################## IMPORTANT! ##################################")
            self._logger.print("################################################################################")
            self._logger.print()
            self._logger.print("You DON'T have enough free space to run Downloader!")
            for partition in full_partitions: self._logger.print(f' - {partition} is FULL')
            self._logger.print()
            if has_system: self._logger.print(f'Minimum required space for {self._config[K_BASE_SYSTEM_PATH]} is {self._config[K_MINIMUM_SYSTEM_FREE_SPACE_MB]}MB.')
            if has_external: self._logger.print(f'Minimum required space for external storage is {self._config[K_MINIMUM_EXTERNAL_FREE_SPACE_MB]}MB.')
            self._logger.print('Free some space and try again. [Waiting 10 seconds...]')
            self._waiter.sleep(10)


    def _needs_reboot(self):
        return self._reboot_calculator.calc_needs_reboot(self._linux_updater.needs_reboot(), self._online_importer.needs_reboot())
