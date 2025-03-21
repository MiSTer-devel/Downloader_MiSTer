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

from pathlib import Path

from downloader.config import default_config
from downloader.full_run_service import FullRunService as ProductionFullRunService
from downloader.fail_policy import FailPolicy
from test.fake_os_utils import SpyOsUtils
from test.fake_waiter import NoWaiter
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_file_system_factory import FileSystemFactory
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger
from test.fake_online_importer import OnlineImporter
from test.fake_reboot_calculator import RebootCalculator
from test.objects import db_empty
from test.fake_certificates_fix import CertificatesFix


class FullRunService(ProductionFullRunService):
    def __init__(
            self,
            config=None,
            file_system_factory=None,
            linux_updater=None,
            os_utils=None,
            certificates_fix=None,
            external_drives_repository=None,
            start_on_db_processing: bool = False,
            fail_policy: FailPolicy = FailPolicy.FAULT_TOLERANT
    ):

        config = config or default_config()
        file_system_factory = FileSystemFactory(config=config) if file_system_factory is None else file_system_factory
        system_file_system = file_system_factory.create_for_system_scope()
        linux_updater = linux_updater or LinuxUpdater(file_system=system_file_system)
        super().__init__(config,
                         NoLogger(),
                         NoLogger(),
                         NoLogger(),
                         LocalRepository(config=config, file_system=system_file_system),
                         OnlineImporter(file_system_factory=file_system_factory, start_on_db_processing=start_on_db_processing, fail_policy=fail_policy),
                         linux_updater,
                         RebootCalculator(file_system=system_file_system),
                         BasePathRelocator(),
                         certificates_fix or CertificatesFix(file_system_factory=file_system_factory),
                         external_drives_repository or ExternalDrivesRepository(file_system=system_file_system),
                         os_utils or SpyOsUtils(),
                         NoWaiter()
                )

    @staticmethod
    def with_single_empty_db() -> ProductionFullRunService:
        config = default_config()
        config.update({
            'databases': {
                db_empty: {
                    'db_url': db_empty,
                    'section': db_empty
                }
            },
            'verbose': False,
            'config_path': Path(''),
            'user_defined_options': [],
            'commit': 'test',
            'fail_on_file_error': True,
        })

        file_system_state = FileSystemState(files={db_empty: {'unzipped_json': {}}})
        file_system_factory = FileSystemFactory(state=file_system_state)

        return FullRunService(
            config,
            file_system_factory=file_system_factory,
        )

    @staticmethod
    def with_single_db(db_id, db_descr, linux_updater=None, update_linux=None, os_utils=None, certificates_fix=None, file_system_factory=None) -> ProductionFullRunService:
        config = FullRunService.single_db_config(db_id, update_linux)
        file_system_factory = file_system_factory or FileSystemFactory(config=config, state=FileSystemState(config=config, files={db_id: {'unzipped_json': db_descr}}))
        return FullRunService(
            config=config,
            linux_updater=linux_updater,
            os_utils=os_utils,
            certificates_fix=certificates_fix,
            file_system_factory=file_system_factory,
        )

    @staticmethod
    def single_db_config(db_id, update_linux=None):
        update_linux = update_linux if update_linux is not None else True
        config = default_config()
        config.update({
                'databases': {
                    db_id: {
                        'db_url': db_id,
                        'section': db_id
                    }
                },
                'verbose': False,
                'user_defined_options': [],
                'config_path': Path(''),
                'commit': 'test',
                'update_linux': update_linux,
                'fail_on_file_error': True
            })
        return config

    @staticmethod
    def with_no_dbs() -> ProductionFullRunService:
        config = default_config()
        config.update({
            'databases': {}, 'verbose': False, 'config_path': Path(''), 'user_defined_options': [],
            'commit': 'test', 'fail_on_file_error': True
        })
        return FullRunService(config)
