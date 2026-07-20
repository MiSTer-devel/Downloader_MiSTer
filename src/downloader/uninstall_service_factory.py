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

from typing import Optional

from downloader.config import Config
from downloader.database_config_remover import DatabaseConfigRemover
from downloader.external_drives_repository import ExternalDrivesRepositoryFactory
from downloader.fail_policy import FailPolicy
from downloader.file_system import FileSystemFactory
from downloader.job_system import ActivityTracker
from downloader.local_repository import LocalRepository
from downloader.logger import Logger, TopLogger
from downloader.migrations import migrations
from downloader.offline_uninstaller import OfflineUninstaller
from downloader.store_migrator import StoreMigrator
from downloader.target_path_calculator import TargetPathsCalculatorFactory
from downloader.uninstall_service import UninstallService
from downloader.update_output import UpdateOutput
from downloader.waiter import Waiter


class UninstallServiceFactory:
    def __init__(
            self,
            logger: Logger,
            update_output: UpdateOutput,
            external_drives_repository_factory: Optional[ExternalDrivesRepositoryFactory] = None,
    ) -> None:
        self._logger = logger
        self._update_output = update_output
        self._external_drives_repository_factory = (
            external_drives_repository_factory or ExternalDrivesRepositoryFactory())

    @staticmethod
    def for_main(top_logger: TopLogger, update_output: UpdateOutput) -> 'UninstallServiceFactory':
        return UninstallServiceFactory(top_logger, update_output)

    def create(self, config: Config) -> UninstallService:
        activity_tracker = ActivityTracker()
        file_system_factory = FileSystemFactory(
            config, {}, self._logger, activity_tracker)
        file_system = file_system_factory.create_for_system_scope()
        external_drives_repository = self._external_drives_repository_factory.create(
            file_system, self._logger)
        store_migrator = StoreMigrator(migrations(config), self._logger)
        local_repository = LocalRepository(
            config,
            self._logger,
            file_system,
            store_migrator,
            external_drives_repository,
            fail_policy=FailPolicy.FAIL_FAST,
        )
        target_paths_calculator = TargetPathsCalculatorFactory(
            file_system,
            external_drives_repository,
            set(),
        ).stored_paths_calculator(config)
        offline_uninstaller = OfflineUninstaller(
            config,
            file_system,
            local_repository,
            Waiter(),
            self._update_output,
            self._logger,
            target_paths_calculator,
        )
        database_config_remover = DatabaseConfigRemover(config, file_system)
        return UninstallService(
            config,
            offline_uninstaller,
            database_config_remover,
            file_system,
            self._update_output,
            self._logger,
        )
