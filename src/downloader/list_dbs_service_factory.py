# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.config import Config
from downloader.file_system import FileSystemFactory
from downloader.job_system import ActivityTracker
from downloader.list_dbs_service import ListDbsService
from downloader.logger import Logger, TopLogger
from downloader.update_output import UpdateOutput


class ListDbsServiceFactory:
    def __init__(self, logger: Logger, update_output: UpdateOutput) -> None:
        self._logger = logger
        self._update_output = update_output

    @staticmethod
    def for_main(top_logger: TopLogger, update_output: UpdateOutput) -> 'ListDbsServiceFactory':
        return ListDbsServiceFactory(top_logger, update_output)

    def create(self, config: Config) -> ListDbsService:
        file_system = FileSystemFactory(config, {}, self._logger, ActivityTracker()).create_for_system_scope()
        return ListDbsService(self._update_output, file_system, self._logger)
