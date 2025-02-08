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
from downloader.free_space_reservation import UnlimitedFreeSpaceReservation
from downloader.full_run_service import FullRunService as ProductionFullRunService
from downloader.importer_command import ImporterCommandFactory
from downloader.interruptions import Interruptions
from downloader.job_system import JobSystem
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import make_downloader_worker_context
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from test.fake_http_gateway import FakeHttpGateway
from test.fake_os_utils import SpyOsUtils
from test.fake_waiter import NoWaiter
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_file_downloader_factory import FileDownloaderFactory
from test.fake_importer_implicit_inputs import FileSystemState, NetworkState
from test.fake_base_path_relocator import BasePathRelocator
from test.fake_file_system_factory import FileSystemFactory
from test.fake_linux_updater import LinuxUpdater
from test.fake_local_repository import LocalRepository
from downloader.logger import NoLogger
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
            file_downloader_factory=None,
            job_system=None,
            file_download_reporter=None,
            installation_report=None,
    ):

        config = config or default_config()
        installation_report = installation_report if installation_report is not None else InstallationReportImpl()
        file_system_factory = FileSystemFactory(config=config) if file_system_factory is None else file_system_factory
        system_file_system = file_system_factory.create_for_system_scope()
        file_downloader_factory = file_downloader_factory or FileDownloaderFactory(file_system_factory=file_system_factory)
        linux_updater = linux_updater or LinuxUpdater(file_system=system_file_system)
        file_download_reporter = file_download_reporter if file_download_reporter is not None else FileDownloadProgressReporter(
            NoLogger(), NoWaiter(), Interruptions(file_system_factory), installation_report
        )
        job_system = job_system if job_system is not None else JobSystem(file_download_reporter, logger=NoLogger(), max_threads=1)
        super().__init__(config,
                         NoLogger(),
                         NoLogger(),
                         NoLogger(),
                         LocalRepository(config=config, file_system=system_file_system),
                         OnlineImporter(file_system_factory=file_system_factory),
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
            file_system_factory=file_system_factory
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
            file_system_factory=file_system_factory
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
