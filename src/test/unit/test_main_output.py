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
from contextlib import redirect_stdout

from downloader.main import main
from test.objects import default_env


class TestMainOutput(unittest.TestCase):

    def test_main___invalid_config_with_ltsv_output___emits_error_event(self):
        env = default_env()
        env['DOWNLOADER_OUTPUT'] = 'DLP1-LTSV'
        env['DEFAULT_DB_ID'] = 'Invalid!'
        env['HTTP_PROXY'] = ''
        env['HTTPS_PROXY'] = ''
        env['ROTATE_LOGS'] = 'true'

        stream = io.StringIO()
        with redirect_stdout(stream):
            exit_code = main(env, 0)

        self.assertEqual(1, exit_code)
        self.assertTrue(stream.getvalue().startswith(
            'DLP1\tevent:error\tcode:config\tmessage:Configuration error: Invalid default_db_id'
        ))
