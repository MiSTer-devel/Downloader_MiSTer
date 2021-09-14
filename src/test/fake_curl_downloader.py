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
from downloader.curl_downloader import CurlCommonDownloader as ProductionCurlCommonDownloader
from test.fake_file_service import FileService
from test.fake_logger import NoLogger
from test.objects import file_MiSTer, file_MiSTer_new


def downloader_with_errors(errors):
    downloader = CurlDownloader()
    for file_path in errors:
        downloader.test_data.errors_at(file_path)
    return downloader


class TestDataCurlDownloader:
    def __init__(self, problematic_files):
        self._problematic_files = problematic_files

    def errors_at(self, file, tries=None):
        self._problematic_files[file] = tries if tries is not None else 99
        return self


class CurlDownloader(ProductionCurlCommonDownloader):
    def __init__(self, config=None, file_service=None, problematic_files=None):
        config = config if config is not None else {'curl_ssl': '', 'downloader_retries': 3}
        self.file_service = FileService() if file_service is None else file_service
        super().__init__(config, self.file_service, NoLogger())
        self._run_files = []
        self._problematic_files = dict() if problematic_files is None else problematic_files

    @property
    def test_data(self):
        return TestDataCurlDownloader(self._problematic_files)

    def _run(self, description, target_path, file):
        self._run_files.append(file)

        if file in self._problematic_files:
            self._problematic_files[file] -= 1

        if file not in self._problematic_files or self._problematic_files[file] <= 0:
            self._file_service.test_data.with_file(file if file != file_MiSTer else file_MiSTer_new, description)
            self._http_oks.append(file)
        else:
            self._errors.append(file)

    def _command(self, target_path, url):
        return target_path

    def _wait(self):
        pass

    def run_files(self):
        return self._run_files