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

import unittest
from downloader.main import run_downloader
from test.fakes import LocalRepository, NoLogger, OnlineImporter, OfflineImporter, LinuxUpdater
from test.fake_db_gateway import DbGateway


class TestRunDownloader(unittest.TestCase):
    def test_run_downloader___no_databases___returns_0(self):
        exit_code = run_downloader(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': []},
            NoLogger(),
            LocalRepository(),
            DbGateway(),
            OfflineImporter(),
            OnlineImporter(),
            LinuxUpdater()
        )
        self.assertEqual(exit_code, 0)

    def test_run_downloader___empty_databases___returns_0(self):
        exit_code = run_downloader(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': [{
                'db_url': 'empty',
                'section': 'empty'
            }]},
            NoLogger(),
            LocalRepository(),
            DbGateway({'empty': {
                'db_id': 'empty',
                'db_files': [],
                'files': [],
                'folders': []
            }}),
            OfflineImporter(),
            OnlineImporter(),
            LinuxUpdater()
        )
        self.assertEqual(exit_code, 0)

    def test_run_downloader___database_with_new_linux___returns_0(self):
        linux_updater = LinuxUpdater()
        exit_code = run_downloader(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': [{
                'db_url': 'empty',
                'section': 'empty'
            }]},
            NoLogger(),
            LocalRepository(),
            DbGateway({'empty': empty_db_with_linux()}),
            OfflineImporter(),
            OnlineImporter(),
            linux_updater
        )
        self.assertEqual(exit_code, 0)

    def test_run_downloader___database_with_wrong_id___returns_1(self):
        exit_code = run_downloader(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': [{
                'db_url': 'empty',
                'section': 'empty'
            }]},
            NoLogger(),
            LocalRepository(),
            DbGateway({'empty': {
                'db_id': 'wrong',
                'db_files': [],
                'files': [],
                'folders': []
            }}),
            OfflineImporter(),
            OnlineImporter(),
            LinuxUpdater()
        )
        self.assertEqual(exit_code, 1)

    def test_run_downloader___database_not_fetched___returns_1(self):
        exit_code = run_downloader(
            {'COMMIT': 'test', 'UPDATE_LINUX': 'false'},
            {'databases': [{
                'db_url': 'empty',
                'section': 'empty'
            }]},
            NoLogger(),
            LocalRepository(),
            DbGateway(),
            OfflineImporter(),
            OnlineImporter(),
            LinuxUpdater()
        )
        self.assertEqual(exit_code, 1)


def empty_db_with_linux():
    return {
        'db_id': 'empty',
        'db_files': [],
        'files': [],
        'folders': [],
        'linux': {
            "delete": [],
            "hash": "d3b619c54c4727ab618bf108013f79d9",
            "size": 83873790,
            "url": "https://raw.githubusercontent.com/MiSTer-devel/SD-Installer-Win64_MiSTer/136d7d8ea24b1de2424574b2d31f527d6b3e3d39/release_20210711.rar",
            "version": "210711"
        }
    }
