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

from downloader.config import FileChecking, default_config
from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE, DB_STATE_SIGNATURE_NO_TIMESTAMP
from test.fake_online_importer import OnlineImporter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from test.objects import store_test_with_file_a_descr, db_test_with_file_a, file_a, file_a_descr, folder_a, db_test, \
    config_with


class TestOnlineImporterSkipDbProcessing(OnlineImporterTestBase):

    def test_download_db_process___when_file_checking_only_on_db_changes_and_signature_from_store_matches_downloaded_signature___does_nothing_and_ends_early(self):
        sut = self.download_db(db_sig=sig(), store_sig=sig(), config=config_with(file_checking=FileChecking.ON_DB_CHANGES))
        self.assertDoesNothingEndsEarly(sut)

    def test_download_db_process___when_default_file_checking_and_signature_from_store_matches_downloaded_signature___does_nothing_and_ends_normally(self):
        sut = self.download_db(db_sig=sig(), store_sig=sig(), config=default_config())
        self.assertDoesNothingEndsNormally(sut)

    def test_download_db_process___when_file_checking_only_on_db_but_signature_from_store_dont_match_db_signature___does_nothing_and_ends_normally_but_requires_save(self):
        for db_sig, store_sig in [
            (sig(size=123), sig(size=456)),
            (sig(timestamp=42), sig(timestamp=30)),
            (sig(db_hash='hash1'), sig(db_hash='hash2'))
        ]:
            with self.subTest(db_sig=db_sig, store_sig=store_sig):
                sut = self.download_db(db_sig=db_sig, store_sig=store_sig, config=config_with(file_checking=FileChecking.ON_DB_CHANGES))
                self.assertDoesNothingEndsNormally(sut, save=True)

    def test_download_db_process___when_file_checking_only_on_db_but_config_filter_has_changed___does_nothing_and_ends_normally_but_requires_save(self):
        identical_sig = sig(filter_value='one')
        sut = self.download_db(db_sig=identical_sig, store_sig=identical_sig, config=config_with(file_checking=FileChecking.ON_DB_CHANGES, filter_value='two'))
        self.assertDoesNothingEndsNormally(sut, save=True)

    def test_download_db_process___when_file_checking_only_on_db_and_signatures_are_identical_but_invalid___does_nothing_and_ends_normally(self):
        for identical_sig in [sig(db_hash=DB_STATE_SIGNATURE_NO_HASH), sig(size=DB_STATE_SIGNATURE_NO_SIZE), sig(timestamp=DB_STATE_SIGNATURE_NO_TIMESTAMP)]:
            with self.subTest(identical_sig=identical_sig):
                sut = self.download_db(db_sig=identical_sig, store_sig=identical_sig, config=config_with(file_checking=FileChecking.ON_DB_CHANGES))
                self.assertDoesNothingEndsNormally(sut)

    def download_db(self, db_sig: dict, store_sig: dict, config: dict) -> OnlineImporter:
        store = store_test_with_file_a_descr()
        sut = OnlineImporter\
            .from_implicit_inputs(ImporterImplicitInputs(files={file_a: file_a_descr()}, folders=[folder_a], config=config))\
            .add_db(db_test_with_file_a(timestamp=db_sig['timestamp']), store, store_sig=store_sig, db_sig=db_sig)\
            .download()
        return sut

    def assertDoesNothingEndsEarly(self, sut: OnlineImporter):
        self.assertReportsNothing(sut, save=False, skipped_dbs=[db_test])

    def assertDoesNothingEndsNormally(self, sut: OnlineImporter, save=False):
        self.assertReportsNothing(sut, save=save, skipped_dbs=[])


def sig(db_hash=None, size=None, timestamp=None, filter_value=None): return {
    'hash': 'match' if db_hash is None else db_hash,
    'size': 456 if size is None else size,
    'timestamp': 42 if timestamp is None else timestamp,
    'filter': '' if filter_value is None else filter_value,
}
