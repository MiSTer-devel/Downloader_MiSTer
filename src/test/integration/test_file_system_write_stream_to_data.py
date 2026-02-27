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

import hashlib
import io
import time
import unittest

from downloader.config import default_config
from downloader.file_system import FsTimeoutError
from test.fake_file_system_factory import make_production_filesystem_factory
from test.fake_stream import StallOnceStream


class TestWriteStreamToData(unittest.TestCase):

    def sut(self, time_monotonic=time.monotonic):
        config = default_config()
        config['base_path'] = '/tmp'
        return make_production_filesystem_factory(config, time_monotonic=time_monotonic).create_for_system_scope()

    def test_write_stream_to_data___with_data___returns_correct_size_and_md5(self):
        data = b'hello world'
        stream = io.BytesIO(data)
        buf, md5 = self.sut().write_stream_to_data(stream, True, 180)
        self.assertEqual(buf.read(), data)
        self.assertEqual(md5, hashlib.md5(data).hexdigest())

    def test_write_stream_to_data___without_md5___returns_empty_hash(self):
        stream = io.BytesIO(b'hello world')
        buf, md5 = self.sut().write_stream_to_data(stream, False, 180)
        self.assertEqual(buf.read(), b'hello world')
        self.assertEqual(md5, '')

    def test_write_stream_to_data___when_stalled_beyond_timeout___raises_timeout_error(self):
        clock = [0.0]
        def fake_monotonic():
            clock[0] += 100.0
            return clock[0]

        stream = StallOnceStream(b'hello world')
        with self.assertRaises(FsTimeoutError):
            self.sut(time_monotonic=fake_monotonic).write_stream_to_data(stream, True, 0)

    def test_write_stream_to_data___when_stall_recovers_within_timeout___returns_data(self):
        clock = [0.0]
        def fake_monotonic():
            clock[0] += 1.0
            return clock[0]

        data = b'hello world'
        stream = StallOnceStream(data)
        buf, md5 = self.sut(time_monotonic=fake_monotonic).write_stream_to_data(stream, True, 180)
        self.assertEqual(buf.read(), data)
        self.assertEqual(md5, hashlib.md5(data).hexdigest())
