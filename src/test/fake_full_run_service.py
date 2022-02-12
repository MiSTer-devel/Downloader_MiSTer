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
from downloader.constants import K_DATABASES, K_DB_URL, K_SECTION, K_VERBOSE, K_CONFIG_PATH, K_USER_DEFINED_OPTIONS, KENV_COMMIT, \
    KENV_UPDATE_LINUX, KENV_FAIL_ON_FILE_ERROR
from downloader.full_run_service import FullRunService as ProductionFullRunService
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_db_gateway import DbGateway
from test.fake_file_system import FileSystemFactory
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger
from test.fake_online_importer import OnlineImporter
from test.fake_offline_importer import OfflineImporter
from test.fake_reboot_calculator import RebootCalculator
from test.fake_store_migrator import StoreMigrator
from test.objects import db_empty
from test.fake_certificates_fix import CertificatesFix


class FullRunService(ProductionFullRunService):
    def __init__(self, env, config, db_gateway, file_system_factory=None):
        self.file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        self.system_file_system = self.file_system_factory.create_for_system_scope()
        super().__init__(env, config,
                         NoLogger(),
                         LocalRepository(config=config, file_system=self.system_file_system),
                         db_gateway,
                         OfflineImporter(file_system_factory=self.file_system_factory),
                         OnlineImporter(file_system=self.system_file_system),
                         LinuxUpdater(self.system_file_system),
                         RebootCalculator(file_system=self.system_file_system),
                         StoreMigrator(),
                         BasePathRelocator(),
                         CertificatesFix())

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
            K_USER_DEFINED_OPTIONS: []
        })

        db_gateway = DbGateway(config)
        db_gateway.file_system.test_data.with_file(db_empty, {'unzipped_json': {}})

        return FullRunService(
            {KENV_COMMIT: 'test', KENV_UPDATE_LINUX: 'false', KENV_FAIL_ON_FILE_ERROR: 'true'},
            config,
            db_gateway,
        )

    @staticmethod
    def with_single_db(db_id, db_descr) -> ProductionFullRunService:
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
                K_CONFIG_PATH: Path('')
            })
        return FullRunService(
            {KENV_COMMIT: 'test', KENV_UPDATE_LINUX: 'false', KENV_FAIL_ON_FILE_ERROR: 'true'},
            config,
            DbGateway.with_single_db(db_id, db_descr, config=config),
        )

    @staticmethod
    def with_no_dbs() -> ProductionFullRunService:
        config = default_config()
        config.update({K_DATABASES: {}, K_VERBOSE: False, K_CONFIG_PATH: Path(''), K_USER_DEFINED_OPTIONS: []})
        return FullRunService(
            {KENV_COMMIT: 'test', KENV_UPDATE_LINUX: 'false', KENV_FAIL_ON_FILE_ERROR: 'true'},
            config,
            DbGateway(config),
        )
