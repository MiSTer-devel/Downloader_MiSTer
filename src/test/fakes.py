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
from test.fake_file_service import FileService
from test.fake_curl_downloader import CurlDownloader, TestDataCurlDownloader
from test.fake_logger import NoLogger
from test.objects import default_env


class ConfigReader(ProductionConfigReader):
    def __init__(self):
        super().__init__(NoLogger(), default_env())


class OnlineImporter(ProductionOnlineImporter):
    def __init__(self, downloader=None, config=None, file_service=None):
        self.file_service = FileService() if file_service is None else file_service
        self._problematic_files = dict()
        config = default_config() if config is None else config
        super().__init__(
            config,
            self.file_service,
            lambda c: CurlDownloader(c, self.file_service, self._problematic_files) if downloader is None else downloader,
            NoLogger())

    @property
    def downloader_test_data(self):
        return TestDataCurlDownloader(self._problematic_files)


class OfflineImporter(ProductionOfflineImporter):
    def __init__(self, config=None, file_service=None):
        self.file_service = FileService() if file_service is None else file_service
        super().__init__(
            default_config() if config is None else config,
            self.file_service,
            NoLogger())


class RebootCalculator(ProductionRebootCalculator):
    def __init__(self, config=None, file_service=None):
        self.file_service = FileService() if file_service is None else file_service
        super().__init__(default_config() if config is None else config, NoLogger(), self.file_service)


class LocalRepository(ProductionLocalRepository):
    def __init__(self, config=None, file_service=None):
        self.file_service = FileService() if file_service is None else file_service
        super().__init__(self._config() if config is None else config, NoLogger(), self.file_service)

    def _config(self):
        config = default_config()
        config['config_path'] = Path('')
        return config


class LinuxUpdater(ProductionLinuxUpdater):
    def __init__(self, file_service=None, downloader=None):
        self.file_service = FileService() if file_service is None else file_service
        self.downloader = CurlDownloader(default_config(), self.file_service) if downloader is None else downloader
        super().__init__(self.file_service, self.downloader, NoLogger())

    def _run_subprocesses(self, linux, linux_path):
        self.file_service.write_file_contents('/MiSTer.version', linux['version'])
        self.file_service.touch('/tmp/downloader_needs_reboot_after_linux_update')
