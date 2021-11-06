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
from .curl_downloader import make_downloader_factory, CurlSerialDownloader
from .local_repository import LocalRepository
from .linux_updater import LinuxUpdater
from .reboot_calculator import RebootCalculator
from .offline_importer import OfflineImporter
from .file_service import FileService
from .db_gateway import DbGateway
from .other import format_files_message, empty_store
from .online_importer import OnlineImporter
from .config import ConfigReader
from .store_migrator import StoreMigrator
from .migrations import migrations


def make_runner(env, logger, ini_path):
    logger.print('START!')
    logger.print()
    logger.print("Reading file: %s" % ini_path)

    config = ConfigReader(logger, env).read_config(ini_path)
    config['curl_ssl'] = env['CURL_SSL']

    file_service = FileService(config, logger)
    local_repository = LocalRepository(config, logger, file_service)

    logger.set_local_repository(local_repository)

    db_gateway = DbGateway(config, file_service, logger)
    downloader_factory = make_downloader_factory(file_service, local_repository, logger)
    offline_importer = OfflineImporter(config, file_service, downloader_factory, logger)
    online_importer = OnlineImporter(config, file_service, downloader_factory, logger)
    linux_updater = LinuxUpdater(file_service, CurlSerialDownloader(config, file_service, local_repository, logger), logger)

    return Runner(
        env,
        config,
        logger,
        local_repository,
        db_gateway,
        offline_importer,
        online_importer,
        linux_updater,
        RebootCalculator(config, logger, file_service),
        StoreMigrator(migrations(), logger)
    )


class Runner:
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

    def run(self):
        start = time.time()

        if self._config['verbose']:
            self._logger.enable_verbose_mode()

        self._logger.debug('env: ' + json.dumps(self._env, indent=4))
        config = self._config.copy()
        config['config_path'] = str(config['config_path'])
        self._logger.debug('config: ' + json.dumps(config, indent=4))

        local_store = self._local_repository.load_store(self._store_migrator)
        failed_dbs = []

        for db_description in self._config['databases']:

            db = self._db_gateway.fetch(db_description['db_url'])

            if not self.validate_db(db, db_description):
                failed_dbs.append(db_description['db_url'])
                continue

            if db['db_id'] not in local_store['dbs']:
                local_store['dbs'][db['db_id']] = empty_store()

            store = local_store['dbs'][db['db_id']]

            self._offline_importer.add_db(db, store)
            self._online_importer.add_db(db, store)
            self._linux_updater.add_db(db)

        if self._env['UPDATE_LINUX'] != 'only':

            self._offline_importer.apply_offline_databases()
            full_resync = not self._local_repository.has_last_successful_run()
            self._online_importer.download_dbs_contents(full_resync)
            self._local_repository.save_store(local_store)
            run_time = str(datetime.timedelta(seconds=time.time() - start))[0:-4]

            self._logger.print()
            self._logger.print('===========================')
            self._logger.print('Downloader 1.2 (%s) by theypsilon. Run time: %ss' % (self._env['COMMIT'], run_time))
            self._logger.print('Log: %s' % self._local_repository.logfile_path)
            self._logger.print()
            self._logger.print('Installed:')
            self._logger.print(format_files_message(self._online_importer.correctly_installed_files()))
            self._logger.print()

            self._logger.print('Errors:')
            self._logger.print(format_files_message(self._online_importer.files_that_failed() + failed_dbs))
        else:
            self._local_repository.save_store(local_store)

        self._logger.print()

        if self._env['UPDATE_LINUX'] != 'false' and self._config.get('update_linux', True):
            self._logger.debug('Running update_linux')
            self._linux_updater.update_linux()
            if self._env['UPDATE_LINUX'] == 'only' and not self._linux_updater.needs_reboot():
                self._logger.print('Linux is already on the latest version.')
                self._logger.print()

        if len(failed_dbs) > 0:
            self._logger.debug('Length of failed_dbs: %d' % len(failed_dbs))
            return 1

        return 0

    def needs_reboot(self):
        return self._reboot_calculator.calc_needs_reboot(self._linux_updater.needs_reboot(), self._online_importer.needs_reboot())

    def validate_db(self, db, db_description):
        if db is None:
            self._logger.debug('ERROR: empty db.')
            return False

        if not isinstance(db, dict):
            self._logger.debug('ERROR: db has incorrect format, contact the db maintainer if this error persists.')
            return False

        if 'db_id' not in db or not isinstance(db['db_id'], str):
            self._logger.print('ERROR: db for section "%s" does not have "db_id", contact the db maintainer.' % db_description['section'])
            return False

        if db['db_id'] != db_description['section']:
            self._logger.print('ERROR: Section "%s" doesn\'t match database id "%s". Fix your INI file.' % (db_description['section'], db['db_id']))
            return False

        if 'zips' not in db or not isinstance(db['zips'], dict):
            self._logger.print('ERROR: db "%s" does not have "zips", contact the db maintainer.' % db['db_id'])
            return False

        if 'db_files' not in db or not isinstance(db['db_files'], list):
            self._logger.print('ERROR: db "%s" does not have "db_files", contact the db maintainer.' % db['db_id'])
            return False

        if 'default_options' not in db or not isinstance(db['default_options'], dict):
            self._logger.print('ERROR: db "%s" does not have "default_options", contact the db maintainer.' % db['db_id'])
            return False

        if 'timestamp' not in db or not isinstance(db['timestamp'], int):
            self._logger.print('ERROR: db "%s" does not have "timestamp", contact the db maintainer.' % db['db_id'])
            return False

        if 'files' not in db or not isinstance(db['files'], dict):
            self._logger.print('ERROR: db "%s" does not have "files", contact the db maintainer.' % db['db_id'])
            return False
        
        if 'folders' not in db or not isinstance(db['folders'], dict):
            self._logger.print('ERROR: db "%s" does not have "folders", contact the db maintainer.' % db['db_id'])
            return False

        if 'base_files_url' not in db or not isinstance(db['base_files_url'], str):
            self._logger.print('ERROR: db "%s" does not have "base_files_url", contact the db maintainer.' % db['db_id'])
            return False

        return True
