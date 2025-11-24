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

from downloader.config import default_config
from downloader.full_run_service import FinalReporter as ProductionFinalReporter
from test.fake_file_system_factory import FileSystemFactory
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger
from test.fake_waiter import NoWaiter


class FinalReporter(ProductionFinalReporter):
    def __init__(self, local_repository=None, config=None):
        config = default_config() if config is None else config
        local_repository = LocalRepository(file_system=FileSystemFactory(config=config).create_for_system_scope(), config=config) if local_repository is None else local_repository
        super().__init__(local_repository, config, NoLogger(), NoWaiter())
