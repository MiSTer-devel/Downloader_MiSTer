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
from downloader.constants import FILE_MiSTer_version, FILE_downloader_needs_reboot_after_linux_update
from downloader.db_entity import DbEntity
from downloader.linux_updater import LinuxUpdater as ProductionLinuxUpdater
from test.fake_waiter import NoWaiter
from test.fake_logger import NoLogger
from test.fake_file_fetcher import SafeFileFetcher
from test.fake_file_system_factory import FileSystemFactory


class LinuxUpdater(ProductionLinuxUpdater):
    def __init__(self, file_system=None, fetcher=None, file_system_factory=None, config=None, network_state=None):
        self._file_system_factory = FileSystemFactory() if file_system_factory is None else file_system_factory
        self.file_system = self._file_system_factory.create_for_system_scope() if file_system is None else file_system
        config = config or default_config()
        fetcher = fetcher or SafeFileFetcher(config, self.file_system, network_state)
        self._dbs = []
        super().__init__(NoLogger(), NoWaiter(), config, self.file_system, fetcher)

    def add_db(self, db: DbEntity) -> 'LinuxUpdater':
        self._dbs.append(db)
        return self

    def update(self) -> 'LinuxUpdater':
        self.update_linux(self._dbs)
        return self

    def _run_subprocesses(self, linux):
        self.file_system.write_file_contents(FILE_MiSTer_version, linux['version'])
        self.file_system.touch(FILE_downloader_needs_reboot_after_linux_update)
