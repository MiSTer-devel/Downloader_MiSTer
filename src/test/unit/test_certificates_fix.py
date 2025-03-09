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

import unittest

from downloader.constants import DEFAULT_CACERT_FILE, K_CURL_SSL, K_BASE_PATH, MEDIA_FAT
from test.fake_file_system_factory import fs_data, FileSystemFactory
from test.fake_certificates_fix import CertificatesFix


class TestCertificatesFix(unittest.TestCase):

    def test_fix_certificates_if_needed___when_is_not_needed_because_no_curl_ssl_options___it_doesnt_download_anything(self):
        sut = CertificatesFix(config={K_CURL_SSL: '', K_BASE_PATH: MEDIA_FAT})
        sut.fix_certificates_if_needed()
        self.assertFalse(sut.download_ran)

    def test_fix_certificates_if_needed___when_is_not_needed_because_cacert_file_is_already_there___it_doesnt_download_anything(self):
        sut = CertificatesFix(file_system_factory=FileSystemFactory.from_state(files={DEFAULT_CACERT_FILE: {}}))
        sut.fix_certificates_if_needed()
        self.assertFalse(sut.download_ran)

    def test_fix_certificates_if_needed___when_is_needed_and_download_works___installs_cacert_file(self):
        sut = CertificatesFix()
        sut.fix_certificates_if_needed()
        self.assertEqual(fs_data(files={DEFAULT_CACERT_FILE: {'hash': DEFAULT_CACERT_FILE, 'size': 1}}), sut.file_system.data)

    def test_fix_certificates_if_needed___when_is_needed_and_download_fails___it_tries_to_download_but_doesnt_install_anything(self):
        sut = CertificatesFix(download_fails=True)
        sut.fix_certificates_if_needed()
        self.assertTrue(sut.download_ran)
        self.assertEqual(fs_data(), sut.file_system.data)

    def test_fix_certificates_if_needed___when_is_needed_and_cacert_test_fails___installs_new_cacert_file(self):
        old_hash = 'old'
        new_hash = DEFAULT_CACERT_FILE

        sut = CertificatesFix(test_query_fails=True, file_system_factory=FileSystemFactory.from_state(files={DEFAULT_CACERT_FILE: {'hash': old_hash}}))

        sut.fix_certificates_if_needed()
        self.assertTrue(sut.download_ran)
        self.assertTrue(sut.test_query_ran)
        self.assertEqual(fs_data(files={DEFAULT_CACERT_FILE: {'hash': new_hash, 'size': 1}}), sut.file_system.data)

    def test_fix_certificates_if_needed___when_is_needed_but_cacert_and_download_fails___it_tries_to_test_and_download_but_doesnt_install_anything(self):
        sut = CertificatesFix(test_query_fails=True, download_fails=True, file_system_factory=FileSystemFactory.from_state(files={DEFAULT_CACERT_FILE: {'hash': 'old'}}))
        sut.fix_certificates_if_needed()
        self.assertTrue(sut.download_ran)
        self.assertTrue(sut.test_query_ran)
        self.assertEqual(fs_data(), sut.file_system.data)
