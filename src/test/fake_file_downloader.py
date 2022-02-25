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

from typing import List

from downloader.constants import K_DOWNLOADER_RETRIES, K_CURL_SSL, K_DEBUG, K_BASE_PATH, MEDIA_FAT
from downloader.file_downloader import CurlDownloaderAbstract, FileDownloaderFactory as ProductionFileDownloaderFactory
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from downloader.target_path_repository import TargetPathRepository
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger


class TestDataCurlDownloader:
    def __init__(self, fake_curl_downloader):
        self._fake_curl_downloader = fake_curl_downloader

    def errors_at(self, file, tries=None):
        self._fake_curl_downloader._problematic_files[file] = tries if tries is not None else 99
        return self

    def brings_file(self, file, description):
        self._fake_curl_downloader._actual_description[file] = description
        return self

    def misses_file(self, file):
        self._fake_curl_downloader._missing_files.add(file)
        return self


class FileDownloader(CurlDownloaderAbstract):
    def __init__(self, config=None, file_system=None):
        config = config if config is not None else {K_CURL_SSL: '', K_DOWNLOADER_RETRIES: 3, K_DEBUG: False, K_BASE_PATH: MEDIA_FAT}
        self.file_system = FileSystemFactory(config=config).create_for_system_scope() if file_system is None else file_system
        self.local_repository = ProductionLocalRepository(config, NoLogger(), self.file_system)
        super().__init__(config, self.file_system, self.local_repository, NoLogger(), True, TargetPathRepository(config, self.file_system))
        self._run_files = []
        self._problematic_files = dict()
        self._actual_description = dict()
        self._missing_files = set()

    @property
    def test_data(self) -> TestDataCurlDownloader:
        return TestDataCurlDownloader(self)

    def _run(self, description, target_path: str, file: str) -> None:
        self._run_files.append(file)

        if file in self._problematic_files:
            self._problematic_files[file] -= 1

        if file not in self._problematic_files or self._problematic_files[file] <= 0:
            if file in self._actual_description:
                description = self._actual_description[file]
            if file not in self._missing_files:
                if hasattr(self._file_system, 'test_data'):
                    self._file_system.test_data.with_file(target_path, description)
                else:
                    self._file_system.write_file_contents(target_path, 'This is a test file.') # Generates a file with hash: test.objects.hash_real_test_file

            self._http_oks.add(file)
        else:
            self._errors.add_print_report(file, '')

    def _command(self, target_path: str, url: str) -> str:
        return target_path

    def _wait(self) -> None:
        pass

    def run_files(self) -> List[str]:
        return self._run_files


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, file_system=None):
        self._file_system = file_system

    def create(self, config, parallel_update, silent=False, hash_check=True):
        return FileDownloader(config, self._file_system)
