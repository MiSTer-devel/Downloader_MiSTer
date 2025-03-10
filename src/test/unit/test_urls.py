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

import unittest

from downloader.other import calculate_url


class TestUrls(unittest.TestCase):

    def test_calculate_urls(self):
        for input_url, input_file_ctx, expected in [
            ['https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/', 'Cheats/AtariLynx/A.P.B. (USA, Europe) [F6FB48FB].zip',
             'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/Cheats/AtariLynx/A.P.B.%20%28USA%2C%20Europe%29%20%5BF6FB48FB%5D.zip'],
            ['https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/', 'Cheats/NES/Lipstick #1 - Lolita Hen (Japan) (Unl) [30D9946C].zip',
             'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/Cheats/NES/Lipstick%20%231%20-%20Lolita%20Hen%20%28Japan%29%20%28Unl%29%20%5B30D9946C%5D.zip'],
            ['https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/', 'Cheats/SNES/Maerchen Adventure Cotton 100% (Japan) [5FB7A31D].zip',
             'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/Cheats/SNES/Maerchen%20Adventure%20Cotton%20100%25%20%28Japan%29%20%5B5FB7A31D%5D.zip'],
            ['   ', 'Cheats/SNES/Maerchen Adventure Cotton 100% (Japan) [5FB7A31D].zip', None],
            [None, 'Cheats/SNES/Maerchen Adventure Cotton 100% (Japan) [5FB7A31D].zip', None],
        ]:
            with self.subTest(input_url) as _:
                self.assertEqual(expected, calculate_url(input_url, input_file_ctx))
