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
from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE
from test.fake_online_importer import OnlineImporter
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase
from test.objects import store_test_with_file_a_descr, db_test_with_file_a, file_a, file_a_descr, folder_a, db_test, \
    config_with


class TestOnlineImporterSkipDbProcessing(OnlineImporterTestBase):
    """
    Specification for database signature-based early exit optimization.

    This test suite provides detailed coverage of the signature matching mechanism used by
    FileChecking.FASTEST mode. For an overview of all file_checking modes, see
    test_online_importer_file_checking.py.

    When file_checking mode is FASTEST, the downloader can skip processing a database
    entirely if its signature matches the store's recorded signature. This optimization
    dramatically speeds up runs when nothing has changed.

    Database signatures include:
    - db_hash: Hash of the database JSON content
    - size: Total size of all files in database
    - timestamp: Database generation timestamp
    - filter: Configuration filter settings

    This test suite validates:
    - Early exit when signatures match (no file operations performed)
    - Normal processing when signatures differ (any component: hash, size, filter)
    - Store updates when signature changes even if files unchanged
    - Filter changes forcing reprocessing despite matching signature
    - Behavior with invalid/missing signature components

    The optimization is critical for reducing download times when databases are
    frequently checked but rarely change.
    """

    def test_download_db_process___when_file_checking_fastest_and_signature_from_store_matches_downloaded_signature___does_nothing_and_ends_early(self):
        sut = self.download_db(db_sig=sig(), store_sig=sig(), config=config_with(file_checking=FileChecking.FASTEST))
        self.assertDoesNothingEndsEarly(sut)

    def test_download_db_process___when_default_file_checking_and_signature_from_store_matches_downloaded_signature___does_nothing_and_ends_normally(self):
        sut = self.download_db(db_sig=sig(), store_sig=sig(), config=default_config())
        self.assertDoesNothingEndsNormally(sut)

    def test_download_db_process___when_file_checking_only_on_db_but_signature_from_store_dont_match_db_signature___does_nothing_and_ends_normally_but_requires_save(self):
        for db_sig, store_sig in [
            (sig(size=123), sig(size=456)),
#            (sig(timestamp=42), sig(timestamp=30)),
            (sig(db_hash='hash1'), sig(db_hash='hash2'))
        ]:
            with self.subTest(db_sig=db_sig, store_sig=store_sig):
                sut = self.download_db(db_sig=db_sig, store_sig=store_sig, config=config_with(file_checking=FileChecking.FASTEST))
                self.assertDoesNothingEndsNormally(sut, save=True)

    def test_download_db_process___when_file_checking_only_on_db_but_config_filter_has_changed___does_nothing_and_ends_normally_but_requires_save(self):
        identical_sig = sig(filter_value='one')
        sut = self.download_db(db_sig=identical_sig, store_sig=identical_sig, config=config_with(file_checking=FileChecking.FASTEST, filter_value='two'))
        self.assertDoesNothingEndsNormally(sut, save=True)

    def test_download_db_process___when_file_checking_only_on_db_and_signatures_are_identical_but_invalid___does_nothing_and_ends_normally(self):
        for identical_sig in [sig(db_hash=DB_STATE_SIGNATURE_NO_HASH), sig(size=DB_STATE_SIGNATURE_NO_SIZE)]:
            with self.subTest(identical_sig=identical_sig):
                sut = self.download_db(db_sig=identical_sig, store_sig=identical_sig, config=config_with(file_checking=FileChecking.FASTEST))
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
