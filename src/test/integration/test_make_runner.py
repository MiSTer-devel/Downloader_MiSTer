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
from downloader.main import make_runner
from test.fakes import NoLogger


class TestRunner(unittest.TestCase):

    def test_make_runner___with_proper_parameters___does_not_throw(self):
        try:
            make_runner({'DEFAULT_DB_URL': '', 'DEFAULT_DB_ID': '', 'ALLOW_REBOOT': 0, 'CURL_SSL': ''}, NoLogger(), '')
        except TypeError:
            self.fail('TypeError during make_runner, composition root failed!')
