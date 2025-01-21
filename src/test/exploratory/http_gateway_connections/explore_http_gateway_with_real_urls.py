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
import signal
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from shutil import copyfileobj
from typing import List

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
    'https://archive.org/download/78_on-the-alamo_isham-jones-harry-radermans-orchestra_gbia0000908b/On%20The%20Alamo%20-%20Isham%20Jones%20-%20Harry%20Radermans%20Orchestra-restored_whisper_asr.json',
    'https://archive.org/download/78_on-the-alamo_isham-jones-harry-radermans-orchestra_gbia0000908b/On%20The%20Alamo%20-%20Isham%20Jones%20-%20Harry%20Radermans%20Orchestra-restored.mp3',
    'https://archive.org/download/78_on-the-alamo_isham-jones-harry-radermans-orchestra_gbia0000908b/On%20The%20Alamo%20-%20Isham%20Jones%20-%20Harry%20Radermans%20Orchestra-restored.png',
    'https://archive.org/download/publicmovies212/Bees_Buzz.webm',
    'https://archive.org/download/publicmovies212/Charlie_Chaplin_Caught_in_a_Caberet.mp4',
]


def main() -> None:
    signals = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT]
    signal_handlers = [(s, signal.getsignal(s)) for s in signals]

    futures: List[Future[None]] = []
    interrupted = False
    cancelled = 0
    def cleanup(interrupt: bool):
        nonlocal interrupted, futures, cancelled
        if interrupt: print('\n\n>>>>>>>>>>>>> INTERRUPTED!! CLEANING UP!\n\n')

        for fut in futures:
            if fut.done():
                e = fut.exception()
                if e is not None:
                    print(e)
            elif not fut.running():
                if fut.cancel():
                    cancelled += 1

        futures = []
        interrupted = True

    def handle_interrupt(signum, frame, phandler):
        cleanup(True)
        if phandler: phandler(signum, frame)

    for sig, cb in signal_handlers:
        signal.signal(sig, lambda s, fr: handle_interrupt(s, fr, cb))

    try:
        logger = PrintLogger.make_configured({'verbose': True, 'start_time': time.time()})
        dir_path = f'{os.path.dirname(os.path.realpath(__file__))}/delme'
        os.makedirs(dir_path, exist_ok=True)

        start = time.time()
        with HttpGateway(ssl_ctx=ssl.create_default_context(), timeout=180, logger=logger) as gateway:
            with ThreadPoolExecutor(max_workers=20) as thread_executor:
                futures = [thread_executor.submit(fetch_url, gateway, input_url, dir_path) for input_url in urls * 20]

                while len(futures) > 0 and not interrupted:
                    next_futures = []
                    for f in futures:
                        if f.done():
                            future_exception = f.exception()
                            if future_exception is not None:
                                print(future_exception)
                        else:
                            next_futures.append(f)

                    futures = next_futures
                    time.sleep(0.5)

                cleanup(False)

        end = time.time()
        print()
        print()
        print(f'Time: {end - start}s')
        print(f'Cancelled {cancelled} tasks.')

    finally:
        for sig, cb in signal_handlers:
            signal.signal(sig, cb)


def fetch_url(gateway: HttpGateway, input_url: str, dir_path: str):
    with gateway.open(input_url) as (url, res):
        if res.status == 200:
            with open(f'{dir_path}/{threading.get_ident()}_{Path(url).name[-30:]}', 'wb') as out_file:
                copyfileobj(res, out_file)


if __name__ == '__main__':
    main()
