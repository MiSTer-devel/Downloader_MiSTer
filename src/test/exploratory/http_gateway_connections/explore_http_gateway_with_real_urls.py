#!/usr/bin/env python3
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

import os
import ssl
import time
from pathlib import Path
from shutil import copyfileobj

from downloader.logger import PrintLogger
from downloader.http_gateway import HttpGateway

urls = [
    'https://google.com',
    'http://google.com',
    'http://www.github.com',
    'https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader.zip',
    'https://github.com/MiSTer-devel/Downloader_MiSTer/releases/download/latest/MiSTer_Downloader_PC_Launcher.zip',
    'https://raw.githubusercontent.com/MiSTer-devel/Downloader_MiSTer/main/dont_download.sh',
    'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip',
    'https://github.com/MiSTer-devel/Distribution_MiSTer/blob/main/db.json.zip?raw=true',
    'https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks',
    'https://www.reddit.com/r/MiSTerFPGA/',
    'https://reddit.com/r/MiSTerFPGA/',
    'http://misterfpga.org/',
    'https://www.misterfpga.org/',
    'https://archive.org/download/78_april-showers_al-jolson-silvers_gbia0006248b/_78_april-showers_al-jolson-silvers_gbia0006248b_02_2.3_CT_EQ.flac',
    'https://archive.org/download/78_april-showers_al-jolson-silvers_gbia0006248b/_78_april-showers_al-jolson-silvers_gbia0006248b_02_2.3_CT_EQ.mp3',
    'https://archive.org/download/78_april-showers_al-jolson-silvers_gbia0006248b/_78_april-showers_al-jolson-silvers_gbia0006248b_02_2.3_CT_EQ.png',
    'https://archive.org/download/publicmovies212/Bees_Buzz.webm',
    'https://archive.org/download/publicmovies212/Charlie_Chaplin_Caught_in_a_Caberet.mp4',
]


def main() -> None:
    logger = PrintLogger.make_configured({'verbose': True, 'start_time': time.time()})
    dir_path = f'{os.path.dirname(os.path.realpath(__file__))}/delme'
    os.makedirs(dir_path, exist_ok=True)

    start = time.time()
    with HttpGateway(ssl_ctx=ssl.create_default_context(), timeout=180, logger=logger) as gateway:
        for input_url in urls * 20:
            try:
                with gateway.open(input_url) as (url, res):
                    if res.status == 200:
                        with open(f'{dir_path}/{Path(url).name[-30:]}', 'wb') as out_file:
                            copyfileobj(res, out_file)
            except Exception as e:
                print(f'Unexpected exception during {input_url}!')
                raise e

    end = time.time()
    print()
    print()
    print(f'Time: {end - start}s')


if __name__ == '__main__':
    main()
