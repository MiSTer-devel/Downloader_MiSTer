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
from downloader.online_importer import OnlineImporter as ProductionOnlineImporter
from downloader.offline_importer import OfflineImporter as ProductionOfflineImporter
from downloader.config import ConfigReader as ProductionConfigReader
from downloader.reboot_calculator import RebootCalculator as ProductionRebootCalculator
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from downloader.linux_updater import LinuxUpdater as ProductionLinuxUpdater
from downloader.runner import Runner as ProductionRunner
from downloader.store_migrator import StoreMigrator as ProductionStoreMigrator
from downloader.migrations import migrations
from test.fake_logger import NoLogger
from test.fake_db_gateway import DbGateway
from test.fake_file_system import FileSystem
from test.fake_file_downloader import FileDownloaderFactory
from test.objects import default_env, db_empty


class ConfigReader(ProductionConfigReader):
    def __init__(self):
        super().__init__(NoLogger(), default_env())


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        self.config = default_config() if config is None else config
        super().__init__(
            self.config,
            self.file_system,
            FileDownloaderFactory(self.config, self.file_system) if file_downloader_factory is None else file_downloader_factory,
            NoLogger())


class OfflineImporter(ProductionOfflineImporter):
    def __init__(self, file_downloader_factory=None, config=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        self.config = default_config() if config is None else config
        super().__init__(
            self.config,
            self.file_system,
            FileDownloaderFactory(self.config, self.file_system) if file_downloader_factory is None else file_downloader_factory,
            NoLogger())


class RebootCalculator(ProductionRebootCalculator):
    def __init__(self, config=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(default_config() if config is None else config, NoLogger(), self.file_system)


class StoreMigrator(ProductionStoreMigrator):
    def __init__(self, maybe_migrations=None):
        super().__init__(migrations() if maybe_migrations is None else maybe_migrations, NoLogger())


class Runner(ProductionRunner):
    def __init__(self, env, config, db_gateway, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(env, config,
                         NoLogger(),
                         LocalRepository(file_system=self.file_system),
                         db_gateway,
                         OfflineImporter(file_system=self.file_system),
                         OnlineImporter(file_system=self.file_system),
                         LinuxUpdater(self.file_system),
                         RebootCalculator(file_system=self.file_system),
                         StoreMigrator())

    @staticmethod
    def with_single_empty_db():
        db_gateway = DbGateway()
        db_gateway.file_system.test_data.with_file(db_empty, {'unzipped_json': {}})
        return Runner(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': {db_empty: {
                'db_url': db_empty,
                'section': db_empty,
                'base_files_url': '',
                'zips': {}
            }}, 'verbose': False, 'config_path': Path('')},
            db_gateway,
        )

    @staticmethod
    def with_single_db(db_id, db_descr):
        return Runner(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': {db_id: {
                'db_url': db_id,
                'section': db_id,
                'base_files_url': '',
                'zips': {}
            }}, 'verbose': False, 'config_path': Path('')},
            DbGateway.with_single_db(db_id, db_descr),
        )

    @staticmethod
    def with_no_dbs():
        return Runner(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': {}, 'verbose': False, 'config_path': Path('')},
            DbGateway(),
        )


class FactoryStub:
    def __init__(self, instance):
        self._instance = instance

    def create(self, *args, **kwargs):
        return self._instance

    def has(self, func):
        func(self._instance)
        return self


class LocalRepository(ProductionLocalRepository):
    def __init__(self, config=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(self._config() if config is None else config, NoLogger(), self.file_system)

    def _config(self):
        config = default_config()
        config['config_path'] = Path('')
        return config


class LinuxUpdater(ProductionLinuxUpdater):
    def __init__(self, file_downloader_factory=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        self.file_downloader_factory = FileDownloaderFactory(default_config(), self.file_system) if file_downloader_factory is None else file_downloader_factory
        super().__init__(self.file_system, self.file_downloader_factory, NoLogger())

    def _run_subprocesses(self, linux, linux_path):
        self.file_system.write_file_contents('/MiSTer.version', linux['version'])
        self.file_system.touch('/tmp/downloader_needs_reboot_after_linux_update')


class Migration:
    def __init__(self, version):
        self.version = version

    def migrate(self, local_store):
        pass

