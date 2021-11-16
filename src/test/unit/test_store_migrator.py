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
from downloader.store_migrator import make_new_local_store, WrongMigrationException
from test.fake_store_migrator import StoreMigrator
from test.fake_migration import Migration


class TestStoreMigratorFixture(unittest.TestCase):

    def test_migrate___on_v0_empty_store___returns_new_empty_store(self):
        store = {}
        sut = StoreMigrator()
        sut.migrate(store)
        self.assertEqual(store, make_new_local_store(sut))

    def test_migrate___with_wrong_migrations___raises_exception(self):
        for migrations in [[Migration(-1)], [Migration(0)], [Migration(2)], [Migration(1), Migration(3)]]:
            with self.subTest():
                self.assertRaises(WrongMigrationException, lambda: StoreMigrator(migrations).migrate({}))

    def test_migrate___with_correct_migrations___does_not_raise_exceptions(self):
        for migrations in [[Migration(1)], [Migration(1), Migration(2)], [Migration(1), Migration(2), Migration(3)]]:
            with self.subTest():
                try:
                    StoreMigrator(migrations).migrate({})
                except WrongMigrationException:
                    self.fail("migrate should not throw.")
