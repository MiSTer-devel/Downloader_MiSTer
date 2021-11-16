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

from pathlib import Path

from downloader.config import default_config
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from test.fake_file_system import FileSystem
from test.fake_logger import NoLogger


class LocalRepository(ProductionLocalRepository):
    def __init__(self, config=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        super().__init__(_config() if config is None else config, NoLogger(), self.file_system)


def _config():
    config = default_config()
    config['config_path'] = Path('')
    return config
