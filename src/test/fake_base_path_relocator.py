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
from downloader.base_path_relocator import BasePathRelocator as ProductionBasePathRelocator
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger
from test.fake_waiter import NoWaiter


class BasePathRelocator(ProductionBasePathRelocator):
    def __init__(self, file_system_factory=None):
        file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        super().__init__(file_system_factory, NoWaiter(), NoLogger())
