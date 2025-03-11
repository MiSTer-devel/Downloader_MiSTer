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
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from test.fake_store_migrator import StoreMigrator
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.objects import config_with
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger


class LocalRepository(ProductionLocalRepository):
    def __init__(self, config=None, file_system=None, store_migrator=None, external_drive_repository=None, file_system_factory=None):
        file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        file_system = file_system_factory.create_for_system_scope() if file_system is None else file_system
        external_drive_repository = ExternalDrivesRepository(file_system=file_system) if external_drive_repository is None else external_drive_repository
        super().__init__(config_with(config_path='') if config is None else config, NoLogger(), file_system, store_migrator or StoreMigrator(), external_drive_repository)
