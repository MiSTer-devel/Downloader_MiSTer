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

from downloader.config import default_config
from downloader.constants import K_DATABASES, K_DB_URL, K_SECTION, K_VERBOSE, K_CONFIG_PATH, K_USER_DEFINED_OPTIONS, \
    K_COMMIT, K_FAIL_ON_FILE_ERROR, K_UPDATE_LINUX
from downloader.full_run_service import FullRunService as ProductionFullRunService
from downloader.importer_command import ImporterCommandFactory
from test.fake_os_utils import SpyOsUtils
from test.fake_waiter import NoWaiter
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_db_gateway import DbGateway
from test.fake_file_system_factory import FileSystemFactory
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from downloader.logger import NoLogger
from test.fake_online_importer import OnlineImporter
from test.fake_offline_importer import OfflineImporter
from test.fake_reboot_calculator import RebootCalculator
from test.objects import db_empty
from test.fake_certificates_fix import CertificatesFix


class FullRunService(ProductionFullRunService):
    def __init__(
            self,
            config=None,
            db_gateway=None,
            file_system_factory=None,
            linux_updater=None,
            os_utils=None,
            certificates_fix=None,
            external_drives_repository=None,
            importer_command_factory=None,
            file_downloader_factory=None):

        config = config or default_config()
        file_system_factory = FileSystemFactory(config=config) if file_system_factory is None else file_system_factory
        system_file_system = file_system_factory.create_for_system_scope()
        file_downloader_factory = file_downloader_factory or FileDownloaderFactory(file_system_factory=file_system_factory)
        linux_updater = linux_updater or LinuxUpdater(file_system=system_file_system, file_downloader_factory=file_downloader_factory)
        super().__init__(config,
                         NoLogger(),
                         LocalRepository(config=config, file_system=system_file_system),
                         db_gateway or DbGateway(config, file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory),
                         OfflineImporter(file_downloader_factory=file_downloader_factory),
                         OnlineImporter(file_system_factory=file_system_factory, file_downloader_factory=file_downloader_factory),
                         linux_updater,
                         RebootCalculator(file_system=system_file_system),
                         BasePathRelocator(),
                         certificates_fix or CertificatesFix(file_system_factory=file_system_factory),
                         external_drives_repository or ExternalDrivesRepository(file_system=system_file_system),
                         os_utils or SpyOsUtils(),
                         NoWaiter(),
                         importer_command_factory or ImporterCommandFactory(config))

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
            K_COMMIT: 'test',
            K_FAIL_ON_FILE_ERROR: True
        })

        file_system_state = FileSystemState(files={db_empty: {'unzipped_json': {}}})
        file_system_factory = FileSystemFactory(state=file_system_state)

        return FullRunService(
            config,
            DbGateway(config, file_system_factory=file_system_factory),
            file_system_factory=file_system_factory
        )

    @staticmethod
    def with_single_db(db_id, db_descr, linux_updater=None, update_linux=None, os_utils=None, certificates_fix=None) -> ProductionFullRunService:
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
                K_FAIL_ON_FILE_ERROR: True
            })
        return FullRunService(
            config,
            DbGateway.with_single_db(db_id, db_descr, config=config),
            linux_updater=linux_updater,
            os_utils=os_utils,
            certificates_fix=certificates_fix
        )

    @staticmethod
    def with_no_dbs() -> ProductionFullRunService:
        config = default_config()
        config.update({
            K_DATABASES: {}, K_VERBOSE: False, K_CONFIG_PATH: Path(''), K_USER_DEFINED_OPTIONS: [],
            K_COMMIT: 'test', K_FAIL_ON_FILE_ERROR: True
        })
        return FullRunService(
            config,
            DbGateway(config),
        )
