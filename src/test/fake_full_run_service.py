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

from pathlib import Path

from downloader.config import default_config, UpdateLinuxEnvironment
from downloader.constants import K_DATABASES, K_DB_URL, K_SECTION, K_VERBOSE, K_CONFIG_PATH, K_USER_DEFINED_OPTIONS, \
    K_COMMIT, K_UPDATE_LINUX_ENVIRONMENT, K_FAIL_ON_FILE_ERROR, K_UPDATE_LINUX
from downloader.full_run_service import FullRunService as ProductionFullRunService
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_db_gateway import DbGateway
from test.fake_file_system_factory import FileSystemFactory
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger
from test.fake_online_importer import OnlineImporter
from test.fake_offline_importer import OfflineImporter
from test.fake_reboot_calculator import RebootCalculator
from test.objects import db_empty
from test.fake_certificates_fix import CertificatesFix


class FullRunService(ProductionFullRunService):
    def __init__(self, config, db_gateway, file_system_factory=None, linux_updater=None):
        file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        system_file_system = file_system_factory.create_for_system_scope()
        file_downloader_factory = FileDownloaderFactory(file_system_factory=file_system_factory)
        linux_updater = linux_updater or LinuxUpdater(system_file_system)
        super().__init__(config,
                         NoLogger(),
                         LocalRepository(config=config, file_system=system_file_system),
                         db_gateway,
                         OfflineImporter(file_downloader_factory=file_downloader_factory),
                         OnlineImporter(file_system_factory=file_system_factory),
                         linux_updater,
                         RebootCalculator(file_system=system_file_system),
                         BasePathRelocator(),
                         CertificatesFix(),
                         ExternalDrivesRepository(file_system=system_file_system))

    @staticmethod
    def with_single_empty_db() -> ProductionFullRunService:
        config = default_config()
        config.update({
            K_DATABASES: {
                db_empty: {
                    K_DB_URL: db_empty,
                    K_SECTION: db_empty,
                    'base_files_url': '',
                    'zips': {}
                }
            },
            K_VERBOSE: False,
            K_CONFIG_PATH: Path(''),
            K_USER_DEFINED_OPTIONS: [],
            K_COMMIT: 'test', K_UPDATE_LINUX_ENVIRONMENT: UpdateLinuxEnvironment.TRUE, K_FAIL_ON_FILE_ERROR: True
        })

        file_system_state = FileSystemState(files={db_empty: {'unzipped_json': {}}})
        file_system_factory = FileSystemFactory(state=file_system_state)

        return FullRunService(
            config,
            DbGateway(config, file_system_factory=file_system_factory),
            file_system_factory=file_system_factory
        )

    @staticmethod
    def with_single_db(db_id, db_descr, linux_updater=None, linux_update_environment=None, update_linux=None) -> ProductionFullRunService:
        update_linux = update_linux if update_linux is not None else True
        config = default_config()
        config.update({
                K_DATABASES: {
                    db_id: {
                        K_DB_URL: db_id,
                        K_SECTION: db_id,
                        'base_files_url': '',
                        'zips': {}
                    }
                },
                K_VERBOSE: False,
                K_USER_DEFINED_OPTIONS: [],
                K_CONFIG_PATH: Path(''),
                K_COMMIT: 'test',
                K_UPDATE_LINUX: update_linux,
                K_UPDATE_LINUX_ENVIRONMENT: linux_update_environment or UpdateLinuxEnvironment.TRUE,
                K_FAIL_ON_FILE_ERROR: True
            })
        return FullRunService(
            config,
            DbGateway.with_single_db(db_id, db_descr, config=config),
            linux_updater=linux_updater
        )

    @staticmethod
    def with_no_dbs() -> ProductionFullRunService:
        config = default_config()
        config.update({
            K_DATABASES: {}, K_VERBOSE: False, K_CONFIG_PATH: Path(''), K_USER_DEFINED_OPTIONS: [],
            K_COMMIT: 'test', K_UPDATE_LINUX_ENVIRONMENT: UpdateLinuxEnvironment.TRUE, K_FAIL_ON_FILE_ERROR: True
        })
        return FullRunService(
            config,
            DbGateway(config),
        )
