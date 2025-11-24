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

from downloader.full_run_service import FileCheckingModeResolver as ProductionFileCheckingModeResolver
from test.fake_file_system_factory import FileSystemFactory
from test.fake_local_repository import LocalRepository
from test.fake_logger import NoLogger


class FileCheckingModeResolver(ProductionFileCheckingModeResolver):
    def __init__(self, local_repository=None, file_system=None, logger=None):
        self.file_system = FileSystemFactory().create_for_system_scope() if file_system is None else file_system
        self.local_repository = LocalRepository(file_system=self.file_system) if local_repository is None else local_repository
        self.logger = NoLogger() if logger is None else logger
        super().__init__(self.local_repository, self.file_system, self.logger)
