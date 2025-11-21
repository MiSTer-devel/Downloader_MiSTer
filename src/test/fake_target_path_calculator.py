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

from typing import Optional
from downloader.config import Config, default_config
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.target_path_calculator import TargetPathsCalculatorFactory as ProductionTargetPathCalculatorFactory
from test.fake_external_drives_repository import ExternalDrivesRepository as FakeExternalDrivesRepository
from test.fake_file_system_factory import FileSystemFactory as FakeFileSystem


class TargetPathCalculatorFactory(ProductionTargetPathCalculatorFactory):
    def __init__(self, file_system: Optional[FileSystem] = None, external_drives_repository: Optional[ExternalDrivesRepository] = None, config: Optional[Config] = None, old_pext_paths: set[str] = None):
        config = config or default_config()
        file_system = file_system or FakeFileSystem(config=config).create_for_config(config)
        external_drives_repository = external_drives_repository or FakeExternalDrivesRepository(file_system=file_system)
        super().__init__(file_system, external_drives_repository, old_pext_paths or set())
