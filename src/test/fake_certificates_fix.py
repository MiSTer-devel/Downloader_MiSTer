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
from downloader.certificates_fix import CertificatesFix as ProductionCertificatesFix
from downloader.constants import default_curl_ssl_options
from test.fake_file_system import FileSystem
from test.fake_logger import NoLogger


class CertificatesFix(ProductionCertificatesFix):
    def __init__(self, config=None, file_system=None, download_fails=False, test_query_fails=False):
        self.file_system = FileSystem() if file_system is None else file_system
        self.download_ran = False
        self.test_query_ran = False
        super().__init__({'curl_ssl': default_curl_ssl_options} if config is None else config, self.file_system, NoLogger())
        self._download_fails = download_fails
        self._test_query_fails = test_query_fails

    def _download(self, path):
        self.file_system.unlink(path)
        self.download_ran = True
        if self._download_fails:
            return FakeResult(1)

        self.file_system.touch(str(path))
        return FakeResult(0)

    def _test_query(self, path):
        self.test_query_ran = True
        if self._test_query_fails:
            return FakeResult(1)

        return FakeResult(0)


class FakeResult:
    def __init__(self, returncode):
        self.returncode = returncode
