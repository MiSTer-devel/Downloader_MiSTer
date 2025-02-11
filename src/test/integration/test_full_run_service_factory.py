# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.config import default_config, AllowReboot
from downloader.constants import K_ALLOW_REBOOT, K_CURL_SSL, K_DEBUG
from downloader.full_run_service_factory import FullRunServiceFactory
from test.fake_logger import NoLogger


class TestFullRunServiceFactory(unittest.TestCase):

    def test_make_full_run_service___with_proper_parameters___does_not_throw(self):
        try:
            FullRunServiceFactory(NoLogger(), NoLogger(), NoLogger()).create({
                **default_config(),
                K_ALLOW_REBOOT: AllowReboot.NEVER,
                K_CURL_SSL: '',
                K_DEBUG: False
            })
        except TypeError:
            self.fail('TypeError during make_full_run_service, composition root failed!')
