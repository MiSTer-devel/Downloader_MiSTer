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

from downloader.config import default_config
from downloader.linux_updater import LinuxUpdater as ProductionLinuxUpdater
from test.fake_file_downloader import FileDownloaderFactory
from test.fake_file_system import FileSystem
from test.fake_logger import NoLogger


class LinuxUpdater(ProductionLinuxUpdater):
    def __init__(self, file_downloader_factory=None, file_system=None):
        self.file_system = FileSystem() if file_system is None else file_system
        self.file_downloader_factory = FileDownloaderFactory(default_config(), self.file_system) if file_downloader_factory is None else file_downloader_factory
        super().__init__(self.file_system, self.file_downloader_factory, NoLogger())

    def _run_subprocesses(self, linux, linux_path):
        self.file_system.write_file_contents('/MiSTer.version', linux['version'])
        self.file_system.touch('/tmp/downloader_needs_reboot_after_linux_update')
