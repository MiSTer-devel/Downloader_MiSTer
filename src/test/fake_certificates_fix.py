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
from downloader.certificates_fix import CertificatesFix as ProductionCertificatesFix
from downloader.config import default_config
from downloader.constants import DEFAULT_CURL_SSL_OPTIONS
from test.fake_waiter import NoWaiter
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger


class CertificatesFix(ProductionCertificatesFix):
    def __init__(self, config=None, download_fails=False, test_query_fails=False, file_system_factory=None):
        self.config = _config() if config is None else config
        self.file_system = FileSystemFactory.from_state(config=self.config).create_for_system_scope() if file_system_factory is None else file_system_factory.create_for_system_scope()
        self.download_ran = False
        self.test_query_ran = False
        super().__init__(self.config, self.file_system, NoWaiter(), NoLogger())
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


def _config():
    config = default_config()
    config['curl_ssl'] = DEFAULT_CURL_SSL_OPTIONS
    return config


class FakeResult:
    def __init__(self, returncode):
        self.returncode = returncode
