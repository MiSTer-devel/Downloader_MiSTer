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

from pathlib import Path

from downloader.config import default_config
from downloader.full_run_service import FullRunService as ProductionFullRunService
from test.fake_db_gateway import DbGateway
from test.fake_file_system import FileSystem
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger
from test.fake_online_importer import OnlineImporter
from test.fake_offline_importer import OfflineImporter
from test.fake_reboot_calculator import RebootCalculator
from test.fake_store_migrator import StoreMigrator
from test.objects import db_empty


class FullRunService(ProductionFullRunService):
    def __init__(self, env, config, db_gateway, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(env, config,
                         NoLogger(),
                         LocalRepository(config=config, file_system=self.file_system),
                         db_gateway,
                         OfflineImporter(file_system=self.file_system),
                         OnlineImporter(file_system=self.file_system),
                         LinuxUpdater(self.file_system),
                         RebootCalculator(file_system=self.file_system),
                         StoreMigrator())

    @staticmethod
    def with_single_empty_db() -> ProductionFullRunService:
        config = default_config()
        config.update({
            'databases': {
                db_empty: {
                    'db_url': db_empty,
                    'section': db_empty,
                    'base_files_url': '',
                    'zips': {}
                }
            },
            'verbose': False,
            'config_path': Path(''),
            'user_defined_options': []
        })

        db_gateway = DbGateway(config)
        db_gateway.file_system.test_data.with_file(db_empty, {'unzipped_json': {}})

        return FullRunService(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false', 'FAIL_ON_FILE_ERROR': 'true'},
            config,
            db_gateway,
        )

    @staticmethod
    def with_single_db(db_id, db_descr) -> ProductionFullRunService:
        config = default_config()
        config.update({
                'databases': {
                    db_id: {
                        'db_url': db_id,
                        'section': db_id,
                        'base_files_url': '',
                        'zips': {}
                    }
                },
                'verbose': False,
                'user_defined_options': [],
                'config_path': Path('')
            })
        return FullRunService(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false', 'FAIL_ON_FILE_ERROR': 'true'},
            config,
            DbGateway.with_single_db(db_id, db_descr, config=config),
        )

    @staticmethod
    def with_no_dbs() -> ProductionFullRunService:
        config = default_config()
        config.update({'databases': {}, 'verbose': False, 'config_path': Path(''), 'user_defined_options': []})
        return FullRunService(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false', 'FAIL_ON_FILE_ERROR': 'true'},
            config,
            DbGateway(config),
        )
