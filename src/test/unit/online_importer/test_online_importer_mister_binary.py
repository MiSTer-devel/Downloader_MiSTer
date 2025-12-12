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

from downloader.constants import FILE_MiSTer_old, FILE_MiSTer, FILE_MiSTer_new, \
    DISTRIBUTION_MISTER_DB_ID
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import fs_data, fs_records
from test.objects import db_distribution_mister, db_test_being_empty_descr, file_mister_descr, empty_test_store, \
    store_descr, hash_MiSTer_old, media_usb0
from test.fake_online_importer import OnlineImporter
from test.unit.online_importer.online_importer_test_base import OnlineImporterTestBase


class TestOnlineImporterMiSTerBinary(OnlineImporterTestBase):
    """
    Specification for MiSTer binary update process and reboot requirement detection.

    The MiSTer binary (main FPGA framework executable) requires special handling during updates:

    - Old binary is preserved as MiSTer.old (backup in case update fails)
    - New binary is downloaded as MiSTer.new then atomically renamed to MiSTer
    - Updates trigger needs_reboot flag since the currently running binary cannot replace itself
    - Process works whether old binary exists or not (fresh install vs update)

    These tests validate that the atomic update sequence is correct and that the reboot flag
    is properly set when the MiSTer binary is installed or updated.
    """

    def test_download_distribution_mister_with_mister___replacing_old_mister_on_empty_store___needs_reboot(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs(
            files={media_usb0(FILE_MiSTer): {'hash': hash_MiSTer_old}},
        ))
        store = empty_test_store()

        sut.add_db(db_distribution_mister(files={FILE_MiSTer: file_mister_descr()}), store)
        sut.download()

        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr()}), store)
        self.assertEqual(fs_data(
            files={
                media_usb0(FILE_MiSTer): file_mister_descr(),
                media_usb0(FILE_MiSTer_old): {'hash': hash_MiSTer_old}
            },
        ), sut.fs_data)
        self.assertEqual(fs_records([
            {'scope': 'write_incoming_stream', 'data': media_usb0(FILE_MiSTer_new)},
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer), media_usb0(FILE_MiSTer_old))},
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer_new), media_usb0(FILE_MiSTer))},
        ]), sut.fs_records)
        self.assertReports(sut, [FILE_MiSTer], needs_reboot=True)

    def test_download_distribution_mister_with_mister___with_no_mister_on_empty_store___needs_reboot2(self):
        sut = OnlineImporter.from_implicit_inputs(ImporterImplicitInputs())
        store = empty_test_store()

        sut.add_db(db_distribution_mister(files={FILE_MiSTer: file_mister_descr()}), store)
        sut.download()

        self.assertEqual(store_descr(db_id=DISTRIBUTION_MISTER_DB_ID, files={FILE_MiSTer: file_mister_descr()}), store)
        self.assertEqual(fs_data(files={media_usb0(FILE_MiSTer): file_mister_descr()}), sut.fs_data)
        self.assertEqual(fs_records([
            {'scope': 'write_incoming_stream', 'data': media_usb0(FILE_MiSTer_new)},
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer_new), media_usb0(FILE_MiSTer))},
        ]), sut.fs_records)
        self.assertReports(sut, [FILE_MiSTer], needs_reboot=True)

    def test_two_databases_one_with_mister___on_empty_store___needs_reboot_and_does_not_throw_due_to_bad_fs_cache_handling(self):
        self.assertReports(OnlineImporter()
                           .add_db(db_distribution_mister(files={FILE_MiSTer: file_mister_descr()}), empty_test_store())
                           .add_db(db_test_being_empty_descr(), empty_test_store())
                           .download(), [FILE_MiSTer], needs_reboot=True)


def fs(files=None, folders=None, base_path=None, config=None):
    return ImporterImplicitInputs(files=files, folders=folders, base_path=base_path, config=config)

