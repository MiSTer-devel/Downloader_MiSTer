# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import io
import unittest

from downloader.update_output import HumanUpdateOutput, LtsvUpdateOutput, update_output_for_mode
from test.fake_logger import NoLogger, SpyLoggerDecorator


class TestUpdateOutput(unittest.TestCase):

    def test_ltsv_update_output___file_start___emits_dlp1_ltsv_line(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_started('distribution_mister', '_Console/Genesis.rbf', 131072, [])

        self.assertEqual(
            'DLP1\tevent:file_start\tdb:distribution_mister\tsize:131072\tpath:_Console/Genesis.rbf\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_start_with_tangle___emits_tangle(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_started('distribution_mister', '_Console/PSX_20250202.rbf', 2915040, ['psx_core'])

        self.assertEqual(
            'DLP1\tevent:file_start\tdb:distribution_mister\tsize:2915040\tpath:_Console/PSX_20250202.rbf\ttangle:psx_core\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_start_with_malformed_tangle___ignores_invalid_tangles(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_started('distribution_mister', '_Console/PSX_20250202.rbf', 2915040, ['psx_core', 1])

        self.assertEqual(
            'DLP1\tevent:file_start\tdb:distribution_mister\tsize:2915040\tpath:_Console/PSX_20250202.rbf\ttangle:psx_core\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_done_for_existing_file___emits_target_existing(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_completed('distribution_mister', '_Console/Genesis.rbf', 131072, True)

        self.assertEqual(
            'DLP1\tevent:file_done\tdb:distribution_mister\tsize:131072\tpath:_Console/Genesis.rbf\ttarget:existing\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_done_for_new_file___emits_target_new(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_completed('distribution_mister', '_Console/PSX_20250202.rbf', 2915040, False)

        self.assertEqual(
            'DLP1\tevent:file_done\tdb:distribution_mister\tsize:2915040\tpath:_Console/PSX_20250202.rbf\ttarget:new\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_remove___emits_dlp1_ltsv_line(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_removed(['distribution_mister'], '/media/fat/_Console/Genesis.rbf', [])

        self.assertEqual(
            'DLP1\tevent:file_remove\tdbs:distribution_mister\tpath:/media/fat/_Console/Genesis.rbf\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_remove_with_tangle___emits_tangle(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_removed(['distribution_mister'], '/media/fat/PSX_20250101.rbf', ['psx_core'])

        self.assertEqual(
            'DLP1\tevent:file_remove\tdbs:distribution_mister\tpath:/media/fat/PSX_20250101.rbf\ttangle:psx_core\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_remove_with_multiple_dbs___sorts_and_emits_dbs(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_removed(['zdb', 'adb'], '/media/fat/foo.txt', [])

        self.assertEqual(
            'DLP1\tevent:file_remove\tdbs:adb,zdb\tpath:/media/fat/foo.txt\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_duplicated_with_multiple_dbs___sorts_dbs_and_emits_machine_event_and_human_line(self):
        stream = io.StringIO()
        logger = SpyLoggerDecorator(NoLogger())
        LtsvUpdateOutput(logger, stream).file_duplicated(['test', 'zdb', 'adb'], 'a/A', 'test')

        self.assertEqual(
            'DLP1\tevent:file_duplicate\tdbs:adb,test,zdb\tpath:a/A\tused:test\n',
            stream.getvalue()
        )
        self.assertEqual([('DUPLICATED: a/A in [adb, test, zdb] [using test instead]',)], logger.printCalls)

    def test_ltsv_update_output___file_done_with_reboot___emits_reboot_true(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_completed('distribution_mister', 'MiSTer', 131072, False, reboot=True)

        self.assertEqual(
            'DLP1\tevent:file_done\tdb:distribution_mister\tsize:131072\tpath:MiSTer\ttarget:new\treboot:true\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___file_done_from_zip___emits_zip_id(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).file_completed('distribution_mister', '_Arcade/game.rom', 131072, False, 'arcade')

        self.assertEqual(
            'DLP1\tevent:file_done\tdb:distribution_mister\tsize:131072\tpath:_Arcade/game.rom\ttarget:new\tzip:arcade\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___unsafe_string_chars___sanitizes_tabs_and_newlines(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).not_overwritten('db\t1', 'folder\nfile\r.txt')

        self.assertEqual(
            'DLP1\tevent:not_overwritten\tdb:db 1\tpath:folder file .txt\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___db_size_add_with_zip___emits_incremental_size_event(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).database_size_added('db1', 1234, 3, 'zip', 'arcade')

        self.assertEqual(
            'DLP1\tevent:db_size_add\tdb:db1\tbytes:1234\tfiles:3\tsrc:zip\tzip:arcade\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___semantic_errors___emits_stable_error_events(self):
        stream = io.StringIO()
        output = LtsvUpdateOutput(NoLogger(), stream)

        output.error('store_load', 'Store failed')
        output.database_failed('db1')
        output.zip_failed('db1', 'zip1')
        output.folder_failed('/media/fat/folder')

        self.assertEqual(
            'DLP1\tevent:error\tcode:store_load\tmessage:Store failed\n'
            'DLP1\tevent:db_fail\tdb:db1\n'
            'DLP1\tevent:zip_fail\tdb:db1\tzip:zip1\n'
            'DLP1\tevent:folder_fail\tpath:/media/fat/folder\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___linux_update_lifecycle___emits_stable_linux_events(self):
        stream = io.StringIO()
        output = LtsvUpdateOutput(NoLogger(), stream)

        output.linux_update_started('distribution_mister', '231030', '240507', 'https://example.com/sd-installer.img.7z')
        output.linux_update_phase('fetch_image')
        output.linux_update_phase('flash')
        output.linux_update_completed()

        self.assertEqual(
            'DLP1\tevent:linux_start\tdb:distribution_mister\tcurrent:231030\tnew:240507\turl:https://example.com/sd-installer.img.7z\n'
            'DLP1\tevent:linux_phase\tphase:fetch_image\n'
            'DLP1\tevent:linux_phase\tphase:flash\n'
            'DLP1\tevent:linux_done\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___linux_update_failed_with_message___emits_phase_and_message(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).linux_update_failed('extract', 'Error code: 101')

        self.assertEqual(
            'DLP1\tevent:linux_fail\tphase:extract\tmessage:Error code: 101\n',
            stream.getvalue()
        )

    def test_ltsv_update_output___linux_update_failed_without_message___emits_phase_only(self):
        stream = io.StringIO()
        LtsvUpdateOutput(NoLogger(), stream).linux_update_failed('user_files')

        self.assertEqual(
            'DLP1\tevent:linux_fail\tphase:user_files\n',
            stream.getvalue()
        )

    def test_human_update_output___linux_update_started___prints_version_transition(self):
        logger = SpyLoggerDecorator(NoLogger())

        HumanUpdateOutput(logger).linux_update_started('distribution_mister', '231030', '240507', 'https://example.com/sd-installer.img.7z')

        self.assertEqual([
            ('Linux will be updated from distribution_mister:',),
            ('Current linux version -> 231030',),
            ('Latest linux version -> 240507',),
            (),
        ], logger.printCalls)

    def test_human_update_output___linux_update_flash_phase___prints_banner_with_recovery_url(self):
        logger = SpyLoggerDecorator(NoLogger())
        output = HumanUpdateOutput(logger)

        output.linux_update_started('distribution_mister', '231030', '240507', 'https://example.com/sd-installer.img.7z')
        logger.printCalls.clear()
        output.linux_update_phase('flash')

        printed = '\n'.join(call[0] if len(call) > 0 else '' for call in logger.printCalls)
        self.assertIn('Stopping this will make your SD unbootable!', printed)
        self.assertIn('https://example.com/sd-installer.img.7z', printed)

    def test_human_update_output___linux_update_failed_with_message___prints_error_and_message(self):
        logger = SpyLoggerDecorator(NoLogger())

        HumanUpdateOutput(logger).linux_update_failed('flash', 'Error code: 1')

        self.assertEqual([
            ('ERROR! Something went wrong during the Linux update, try again later.',),
            ('Error code: 1',),
            (),
        ], logger.printCalls)

    def test_human_update_output___error___adds_human_error_prefix(self):
        logger = SpyLoggerDecorator(NoLogger())

        HumanUpdateOutput(logger).error('store_load', 'Store failed')

        self.assertEqual([('ERROR: Store failed',)], logger.printCalls)

    def test_human_update_output___file_start___prints_same_human_line(self):
        logger = SpyLoggerDecorator(NoLogger())

        HumanUpdateOutput(logger).file_started('distribution_mister', '_Console/Genesis.rbf', 131072, [])

        self.assertEqual([('_Console/Genesis.rbf',)], logger.printCalls)

    def test_human_update_output___file_duplicated___prints_duplicated_line_with_dbs_and_winner(self):
        logger = SpyLoggerDecorator(NoLogger())

        HumanUpdateOutput(logger).file_duplicated(['test', 'bar'], 'a/A', 'test')

        self.assertEqual([('DUPLICATED: a/A in [test, bar] [using test instead]',)], logger.printCalls)

    def test_human_update_output___run_started___logs_human_message(self):
        logger = SpyLoggerDecorator(NoLogger())
        update_output_for_mode('human', logger).run_started('2.4', 'abc123')

        self.assertEqual([('START!',), ()], logger.printCalls)

    def test_ltsv_update_output___run_started___emits_machine_event_and_logs_human_message(self):
        stream = io.StringIO()
        logger = SpyLoggerDecorator(NoLogger())
        LtsvUpdateOutput(logger, stream).run_started('2.4', 'abc123')

        self.assertEqual('DLP1\tevent:run_start\tversion:2.4\tcommit:abc123\n', stream.getvalue())
        self.assertEqual([('START!',), ()], logger.printCalls)

    def test_update_output_for_mode___dlp1_ltsv___returns_ltsv_output(self):
        self.assertIsInstance(update_output_for_mode('dlp1-ltsv', NoLogger()), LtsvUpdateOutput)
        self.assertIsInstance(update_output_for_mode('DLP1-LTSV', NoLogger()), LtsvUpdateOutput)

    def test_update_output_for_mode___human_or_unknown___returns_human_output(self):
        self.assertIsInstance(update_output_for_mode('human', NoLogger()), HumanUpdateOutput)
        self.assertIsInstance(update_output_for_mode('wat', NoLogger()), HumanUpdateOutput)
