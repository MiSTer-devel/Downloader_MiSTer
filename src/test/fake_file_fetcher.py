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

from typing import Optional
from downloader.config import Config
from downloader.file_system import FileSystem
from downloader.jobs.fetch_file_worker import SafeFileFetcher as ProductionSafeFileFetcher
from downloader.logger import NoLogger
from test.fake_http_gateway import FakeHttpGateway
from test.fake_importer_implicit_inputs import NetworkState
from test.fake_waiter import NoWaiter


class SafeFileFetcher(ProductionSafeFileFetcher):
    def __init__(self, config: Config, file_system: FileSystem, network_state: Optional[NetworkState] = None):
        self._file_system = file_system
        self._http_gateway = FakeHttpGateway(config, network_state or NetworkState())
        super().__init__(config, file_system, NoLogger(), self._http_gateway, NoWaiter())

    def fetch_file(self, description, path):
        self._http_gateway.set_file_ctx({
            'description': description.copy(),
            'path': path
        })
        result = super().fetch_file(description, path)
        self._http_gateway.set_file_ctx(None)
        return result
