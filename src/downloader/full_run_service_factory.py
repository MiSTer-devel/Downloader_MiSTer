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

from downloader.config import ConfigReader
from downloader.db_gateway import DbGateway
from downloader.file_downloader import make_file_downloader_factory
from downloader.file_filter import FileFilterFactory
from downloader.file_system import FileSystem
from downloader.full_run_service import FullRunService
from downloader.linux_updater import LinuxUpdater
from downloader.local_repository import LocalRepository
from downloader.migrations import migrations
from downloader.offline_importer import OfflineImporter
from downloader.online_importer import OnlineImporter
from downloader.reboot_calculator import RebootCalculator
from downloader.store_migrator import StoreMigrator


def make_full_run_service(env, logger, ini_path):
    logger.print('START!')
    logger.print()
    logger.print("Reading file: %s" % ini_path)

    config = ConfigReader(logger, env).read_config(ini_path)
    config['curl_ssl'] = env['CURL_SSL']

    file_system = FileSystem(config, logger)
    local_repository = LocalRepository(config, logger, file_system)

    logger.set_local_repository(local_repository)

    file_filter_factory = FileFilterFactory()
    file_downloader_factory = make_file_downloader_factory(file_system, local_repository, logger)
    db_gateway = DbGateway(config, file_system, file_downloader_factory, logger)
    offline_importer = OfflineImporter(file_system, file_downloader_factory, logger)
    online_importer = OnlineImporter(file_filter_factory, file_system, file_downloader_factory, logger)
    linux_updater = LinuxUpdater(config, file_system, file_downloader_factory, logger)
    store_migrator = StoreMigrator(migrations(file_system), logger)

    return FullRunService(
        env,
        config,
        logger,
        local_repository,
        db_gateway,
        offline_importer,
        online_importer,
        linux_updater,
        RebootCalculator(config, logger, file_system),
        store_migrator
    )
