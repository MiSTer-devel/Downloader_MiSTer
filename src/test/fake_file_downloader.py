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

from downloader.file_downloader import CurlDownloaderAbstract, FileDownloaderFactory as ProductionFileDownloaderFactory
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from test.fake_file_system import FileSystem
from test.fake_logger import NoLogger
from test.objects import file_MiSTer, file_MiSTer_new


def downloader_with_errors(errors):
    downloader = FileDownloader()
    for file_path in errors:
        downloader.test_data.errors_at(file_path)
    return downloader


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
        config = config if config is not None else {'curl_ssl': '', 'downloader_retries': 3}
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(config, self.file_system, ProductionLocalRepository(config, NoLogger(), self.file_system), NoLogger(), True)
        self._run_files = []
        self._problematic_files = dict()
        self._actual_description = dict()
        self._missing_files = set()

    @property
    def test_data(self):
        return TestDataCurlDownloader(self)

    def _run(self, description, target_path, file):
        self._run_files.append(file)

        if file in self._problematic_files:
            self._problematic_files[file] -= 1

        if file not in self._problematic_files or self._problematic_files[file] <= 0:
            if file in self._actual_description:
                description = self._actual_description[file]
            if file not in self._missing_files:
                self._file_system.test_data.with_file(file if file != file_MiSTer else file_MiSTer_new, description)
            self._http_oks.add(file)
        else:
            self._errors.add_print_report(file, '')

    def _command(self, target_path, url):
        return target_path

    def _wait(self):
        pass

    def run_files(self):
        return self._run_files


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, config=None, file_system=None):
        self._config = config
        self._file_system = file_system

    def create(self, parallel_update, silent=False, hash_check=True):
        return FileDownloader(self._config, self._file_system)
