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
import json
import sys
import tempfile
import unittest
import os
from pathlib import Path
from test.fake_file_system import make_production_filesystem
from downloader.config import AllowDelete, default_config

not_created_file = '/tmp/opened_file'
empty_file = '/tmp/empty_file'
empty_file_hash = 'd41d8cd98f00b204e9800998ecf8427e'
mister_file = 'MiSTer'
rbf_file = 'MyCore.RBF'
foo_bar_json = {"foo": "bar"}


class TestFileSystem(unittest.TestCase):

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        Path(empty_file).touch()

    def tearDown(self) -> None:
        self.tempdir.cleanup()
        unlink(not_created_file)
        unlink(empty_file)

    def test_is_file___on_nothing__returns_false(self):
        self.assertFalse(self.sut().is_file('this_will_never_be_a_file.sh'))

    def test_is_file___on_read_file_contents__returns_content(self):
        self.sut().touch(not_created_file)
        actual = self.sut().read_file_contents(not_created_file)
        self.assertEqual(actual, '')

    def test_is_file___on_touched_file__returns_true(self):
        self.sut().touch(not_created_file)
        self.assertTrue(self.sut().is_file(not_created_file))

    def test_hash___on_empty_file__returns_same_string_always(self):
        self.assertEqual(self.sut().hash(empty_file), empty_file_hash)

    def test_hash___on_bigger_file__returns_different_string(self):
        self.assertNotEqual(self.sut({'base_path': '..'}).hash('downloader.sh'), empty_file_hash)

    def test_move___on_existing_file__works_fine(self):
        self.sut().move(empty_file, not_created_file)
        self.assertTrue(self.sut().is_file(not_created_file))
        self.assertFalse(self.sut().is_file(empty_file))

    def test_copy___on_existing_file__works_fine(self):
        self.sut().copy(empty_file, not_created_file)
        self.assertTrue(self.sut().is_file(not_created_file))
        self.assertTrue(self.sut().is_file(empty_file))

    def test_unlink_mister___when_allow_delete_only_rbf___keeps_it(self):
        sut = self.sut(self.default_test_config(allow_delete=AllowDelete.OLD_RBF))

        sut.makedirs_parent(mister_file)
        sut.touch(mister_file)
        self.assertTrue(sut.is_file(mister_file))

        sut.unlink(mister_file)
        self.assertTrue(sut.is_file(mister_file))

    def test_unlink_mister_file___when_allow_delete_none___doesnt_delete_it(self):
        sut = self.sut(self.default_test_config(allow_delete=AllowDelete.NONE))

        sut.makedirs_parent(mister_file)
        sut.touch(mister_file)
        self.assertTrue(sut.is_file(mister_file))

        sut.unlink(mister_file)
        self.assertTrue(sut.is_file(mister_file))

    def test_unlink_rbf_file___when_allow_delete_only_rbf___deletes_it(self):
        sut = self.sut(self.default_test_config(allow_delete=AllowDelete.OLD_RBF))

        sut.makedirs_parent(rbf_file)
        sut.touch(rbf_file)
        self.assertTrue(sut.is_file(rbf_file))

        sut.unlink(rbf_file)
        self.assertFalse(sut.is_file(rbf_file))

    def test_unlink_something_else___when_allow_delete_only_rbf___doesnt_delete_it(self):
        sut = self.sut(self.default_test_config(allow_delete=AllowDelete.OLD_RBF))

        sut.makedirs_parent(empty_file)
        sut.touch(empty_file)
        self.assertTrue(sut.is_file(empty_file))

        sut.unlink(empty_file)
        self.assertTrue(sut.is_file(empty_file))

    def test_unlink_anything___with_default_config___deletes_it(self):
        self.sut().touch(empty_file)
        self.assertTrue(self.sut().is_file(empty_file))

        self.sut().unlink(empty_file)
        self.assertFalse(self.sut().is_file(empty_file))

    def test_curl_path_x___after_add_system_path_x_with_system_path_b___returns_b_plus_x(self):
        sut = self.sut({'base_path': 'a', 'base_system_path': 'b'})
        sut.add_system_path('x')
        self.assertEqual(sut.download_target_path('x'), 'b/x')

    def test_curl_path_x___with_system_path_a___returns_a_plus_x(self):
        sut = self.sut({'base_path': 'a', 'base_system_path': 'b'})
        self.assertEqual(sut.download_target_path('x'), 'a/x')

    def test_curl_path_temp_x___always___returns_temp_plus_x(self):
        self.assertEqual(self.sut().download_target_path('/tmp/x'), '/tmp/x')

    def test_makedirs___on_missing_folder___creates_it(self):
        self.sut().makedirs('foo')
        self.assertTrue(os.path.isdir(str(Path(self.tempdir.name) / 'foo')))

    def test_load_dict_from_file___on_plain_json___returns_json_dict(self):
        json_file = 'foo.json'
        self.sut().write_file_contents(json_file, json.dumps(foo_bar_json))
        self.assertEqual(foo_bar_json.copy(), self.sut().load_dict_from_file(json_file))

    @unittest.skipUnless(sys.platform.startswith("linux"), "requires Linux")
    def test_load_dict_from_file___on_zipped_json___returns_json_dict(self):
        zip_file = 'foo.json.zip'
        self.sut().save_json_on_zip(foo_bar_json.copy(), zip_file)
        self.assertEqual(foo_bar_json.copy(), self.sut().load_dict_from_file(zip_file))

    def sut(self, config=None):
        return make_production_filesystem(self.default_test_config() if config is None else config)

    def default_test_config(self, allow_delete=None):
        actual_config = default_config()
        actual_config['base_path'] = self.tempdir.name
        actual_config['base_system_path'] = self.tempdir.name
        if allow_delete is not None:
            actual_config['allow_delete'] = allow_delete
        return actual_config


def unlink(file):
    try:
        Path(file).unlink()
    except FileNotFoundError as _:
        pass
