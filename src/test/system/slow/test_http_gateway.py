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
import ssl
import tempfile
import time
import random
import shutil
import os
import os.path
from pathlib import Path

from downloader.constants import DISTRIBUTION_MISTER_DB_URL
from downloader.http_gateway import HttpGateway
from downloader.logger import PrintLogger
from downloader.other import calculate_url
from downloader.file_system import load_json_from_zip


class TestHttpGateway(unittest.TestCase):
    dir_path = f'{os.path.dirname(os.path.realpath(__file__))}/delme'

    def setUp(self) -> None:
        shutil.rmtree(self.dir_path, ignore_errors=True)
        os.makedirs(self.dir_path)

    def tearDown(self) -> None:
        shutil.rmtree(self.dir_path)

    def test_http_gateway_with_distribution_mister_urls___gets_500_files(self):
        with HttpGateway(ssl_ctx=ssl.create_default_context(), timeout=180, logger=PrintLogger()) as gateway:
            with tempfile.NamedTemporaryFile() as temp_file, gateway.open(DISTRIBUTION_MISTER_DB_URL) as (url, res):
                shutil.copyfileobj(res, temp_file)
                db = load_json_from_zip(temp_file.name)
                urls = [calculate_url(db['base_files_url'], file.replace('|', '')) for file in db['files']]

            random.Random(42).shuffle(urls)

            failed_urls = []
            fetched_files = []
            for index, input_url in enumerate(urls[0:500]):
                with gateway.open(input_url) as (url, res):
                    if res.status == 200:
                        filename = f'{index}{Path(url).suffix}'
                        with open(f'{self.dir_path}/{filename}', 'wb') as out_file:
                            shutil.copyfileobj(res, out_file)
                        fetched_files.append(filename)
                    else:
                        failed_urls.append(input_url)

        self.assertEqual([], failed_urls)
        self.assertEqual(500, len(fetched_files))
        self.assertEqual(sorted(os.listdir(self.dir_path)), sorted(fetched_files))
