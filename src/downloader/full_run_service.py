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

import datetime
import time
import json

from downloader.importer_command import ImporterCommand
from downloader.other import format_files_message, empty_store


class FullRunService:
    def __init__(self, env, config, logger, local_repository, db_gateway, offline_importer, online_importer, linux_updater, reboot_calculator, store_migrator):
        self._store_migrator = store_migrator
        self._reboot_calculator = reboot_calculator
        self._linux_updater = linux_updater
        self._online_importer = online_importer
        self._offline_importer = offline_importer
        self._db_gateway = db_gateway
        self._local_repository = local_repository
        self._logger = logger
        self._env = env
        self._config = config

    def full_run(self):
        start_time = time.time()

        if self._config['verbose']:
            self._logger.enable_verbose_mode()

        self._debug_log_initial_state()

        local_store = self._local_repository.load_store(self._store_migrator)

        databases, failed_dbs = self._db_gateway.fetch_all(self._config['databases'])

        importer_command = ImporterCommand(self._config, self._config['user_defined_options'])
        for db in databases:
            if db.db_id not in local_store['dbs']:
                local_store['dbs'][db.db_id] = empty_store()

            store = local_store['dbs'][db.db_id]
            description = self._config['databases'][db.db_id]

            importer_command.add_db(db, store, description)

        update_only_linux = self._env['UPDATE_LINUX'] == 'only'
        update_linux = self._env['UPDATE_LINUX'] != 'false' and self._config.get('update_linux', True)

        if not update_only_linux:
            full_resync = not self._local_repository.has_last_successful_run()

            self._offline_importer.apply_offline_databases(importer_command)
            self._online_importer.download_dbs_contents(importer_command, full_resync)

        self._local_repository.save_store(local_store)

        if not update_only_linux:
            self._display_summary(self._online_importer.correctly_installed_files(),
                                  self._online_importer.files_that_failed() + failed_dbs, start_time)

        self._logger.print()

        if update_linux:
            self._linux_updater.update_linux(importer_command)

        if update_only_linux and not self._linux_updater.needs_reboot():
            self._logger.print('Linux is already on the latest version.')
            self._logger.print()

        if self._env['FAIL_ON_FILE_ERROR'] == 'true' and len(self._online_importer.files_that_failed()) > 0:
            self._logger.debug('Length of files_that_failed: %d' % len(self._online_importer.files_that_failed()))
            self._logger.debug('Length of failed_dbs: %d' % len(failed_dbs))
            return 1

        if len(failed_dbs) > 0:
            self._logger.debug('Length of failed_dbs: %d' % len(failed_dbs))
            return 1

        return 0

    def _debug_log_initial_state(self):
        self._logger.debug('env: ' + json.dumps(self._env, indent=4))
        config = self._config.copy()
        config['config_path'] = str(config['config_path'])
        self._logger.debug('config: ' + json.dumps(config, default=lambda o: o.__dict__, indent=4))

    def _display_summary(self, installed_files, failed_files, start_time):
        run_time = str(datetime.timedelta(seconds=time.time() - start_time))[0:-4]

        self._logger.print()
        self._logger.print('===========================')
        self._logger.print('Downloader 1.3 (%s) by theypsilon. Run time: %ss' % (self._env['COMMIT'], run_time))
        self._logger.print('Log: %s' % self._local_repository.logfile_path)
        self._logger.print()
        self._logger.print('Installed:')
        self._logger.print(format_files_message(installed_files))
        self._logger.print()
        self._logger.print('Errors:')
        self._logger.print(format_files_message(failed_files))

    def needs_reboot(self):
        return self._reboot_calculator.calc_needs_reboot(self._linux_updater.needs_reboot(), self._online_importer.needs_reboot())
