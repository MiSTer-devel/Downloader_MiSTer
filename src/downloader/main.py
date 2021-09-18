#!/usr/bin/env python3
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

import time
import datetime
import subprocess
import traceback

from .config import config_file_path, ConfigReader
from .online_importer import OnlineImporter
from .logger import Logger
from .curl_downloader import make_downloader_factory, CurlSerialDownloader
from .local_repository import LocalRepository
from .linux_updater import LinuxUpdater
from .reboot_calculator import RebootCalculator
from .offline_importer import OfflineImporter
from .file_service import FileService
from .db_gateway import DbGateway
from .other import format_files_message, empty_store


def main(env):
    logger = Logger()
    try:
        exit_code = main_internal(env, logger)
    except Exception as _:
        logger.print(traceback.format_exc())
        exit_code = 1

    logger.close_logfile()
    return exit_code


def main_internal(env, logger):
    logger.print('START!')

    ini_path = config_file_path(env['DOWNLOADER_LAUNCHER_PATH'])

    logger.print()
    logger.print("Reading file: %s" % ini_path)

    config = ConfigReader(logger, env).read_config(ini_path)
    config['curl_ssl'] = env['CURL_SSL']

    file_service = FileService(config, logger)
    local_repository = LocalRepository(config, logger, file_service)

    logger.set_local_repository(local_repository)

    db_gateway = DbGateway(config, file_service, logger)
    offline_importer = OfflineImporter(config, file_service, logger)
    online_importer = OnlineImporter(config, file_service, make_downloader_factory(file_service, local_repository, logger), logger)
    linux_updater = LinuxUpdater(file_service, CurlSerialDownloader(config, file_service, local_repository, logger), logger)

    exit_code = run_downloader(
        env,
        config,
        logger,
        local_repository,
        db_gateway,
        offline_importer,
        online_importer,
        linux_updater
    )

    needs_reboot = RebootCalculator(config, logger, file_service).calc_needs_reboot(
        linux_updater.needs_reboot(),
        online_importer.needs_reboot())

    if needs_reboot:
        logger.print()
        logger.print("Rebooting in 10 seconds...")
        time.sleep(2)
        logger.close_logfile()
        time.sleep(4)
        subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
        time.sleep(4)
        subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)
        time.sleep(30)
        subprocess.run(['reboot', 'now'], shell=False, stderr=subprocess.STDOUT)

    return exit_code


def run_downloader(env, config, logger, local_repository, db_gateway, offline_importer, online_importer, linux_updater):
    start = time.time()

    local_store = local_repository.load_store()
    failed_dbs = []

    for db_description in config['databases']:

        db = db_gateway.fetch(db_description['db_url'])
        if db is None:
            failed_dbs.append(db_description['db_url'])
            continue

        if db['db_id'] != db_description['section']:
            failed_dbs.append(db_description['db_url'])
            logger.print('Section %s doesn\'t match database id "%s"' % (db_description['section'], db['db_id']))
            continue

        if db['db_id'] not in local_store:
            local_store[db['db_id']] = empty_store()

        store = local_store[db['db_id']]

        offline_importer.add_db(db, store)
        online_importer.add_db(db, store)
        linux_updater.add_db(db)

    if env['UPDATE_LINUX'] != 'only':

        offline_importer.apply_offline_databases()
        full_resync = not local_repository.has_last_successful_run()
        online_importer.download_dbs_contents(full_resync)

        run_time = str(datetime.timedelta(seconds=time.time() - start))[0:-4]

        logger.print()
        logger.print('===========================')
        logger.print('Downloader 1.0 (%s) by theypsilon. Run time: %ss' % (env['COMMIT'], run_time))
        logger.print('Log: %s' % local_repository.logfile_path)
        logger.print()
        logger.print('Installed:')
        logger.print(format_files_message(online_importer.correctly_installed_files()))
        logger.print()

        logger.print('Errors:')
        logger.print(format_files_message(online_importer.files_that_failed() + failed_dbs))

    logger.print()
    local_repository.save_store(local_store)

    if env['UPDATE_LINUX'] != 'false' and config.get('update_linux', True):
        linux_updater.update_linux()
        if env['UPDATE_LINUX'] == 'only' and not linux_updater.needs_reboot():
            logger.print('Linux is already on the latest version.')
            logger.print()

    if len(failed_dbs) > 0:
        return 1

    return 0
