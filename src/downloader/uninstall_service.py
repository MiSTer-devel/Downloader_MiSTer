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
from downloader.constants import EXIT_ERROR_UNINSTALL_DRIVE_DISCONNECTED, \
    EXIT_ERROR_UNINSTALL_EXTERNALS_UNVERIFIED, EXIT_ERROR_WRONG_SETUP
from downloader.database_config_remover import DatabaseConfigRemover, \
    DatabaseConfigRemovalResult, DatabaseReappearanceReason
from downloader.file_system import FileSystem
from downloader.logger import Logger
from downloader.offline_uninstaller import OfflineUninstaller, UninstallBox
from downloader.other import remove_run_signal
from downloader.update_output import UpdateOutput


class UninstallService:
    def __init__(self, config: Config, offline_uninstaller: OfflineUninstaller, database_config_remover: DatabaseConfigRemover, file_system: FileSystem, update_output: UpdateOutput, logger: Logger) -> None:
        self._config = config
        self._offline_uninstaller = offline_uninstaller
        self._database_config_remover = database_config_remover
        self._file_system = file_system
        self._update_output = update_output
        self._logger = logger

    def uninstall(self, db_ids: list[str], force: bool = False) -> int:
        result, removed_bytes, removed_files = self._uninstall(db_ids, force)
        remove_run_signal(self._file_system, self._logger)
        self._update_output.uninstall_finished(result, removed_bytes, removed_files)
        return result

    def _uninstall(
            self,
            db_ids: list[str],
            force: bool,
    ) -> tuple[int, int, int]:
        normalized = self._normalize_db_ids(db_ids)
        if not normalized:
            self._update_output.error('uninstall_no_db_ids', 'No database ids given.')
            return EXIT_ERROR_WRONG_SETUP, 0, 0

        box = self._offline_uninstaller.uninstall_dbs(normalized, force)
        removed_bytes = box.removed_bytes()
        removed_files = box.removed_files()
        if box.error() is not None:
            self._update_output.error('unexpected')
            return 1, removed_bytes, removed_files

        invalid = box.invalid_db_ids()
        if invalid:
            self._update_output.error(
                'uninstall_invalid_db_ids',
                'Invalid database ids: ' + ', '.join(invalid),
            )
            return EXIT_ERROR_WRONG_SETUP, removed_bytes, removed_files

        result = self._result_for_box(box)
        if not box.save_failed():
            for db_id in box.uninstalled_db_ids():
                removal = self._database_config_remover.remove(db_id)
                self._report_config_removal(db_id, removal)
                if removal.failures:
                    result = 1
        return result, removed_bytes, removed_files

    @staticmethod
    def _result_for_box(box: UninstallBox) -> int:
        refused = box.refused_db_ids()
        failed = box.failed_db_ids()
        disconnected = box.drive_disconnected_db_ids()
        if box.save_failed():
            return 1
        if refused and not failed:
            return EXIT_ERROR_UNINSTALL_EXTERNALS_UNVERIFIED
        if disconnected and set(disconnected) == set(failed) and not refused:
            return EXIT_ERROR_UNINSTALL_DRIVE_DISCONNECTED
        if refused or failed:
            return 1
        return 0

    def _normalize_db_ids(self, db_ids: list[str]) -> list[str]:
        configured = {db_id.lower(): db_id for db_id in self._config['databases']}
        normalized: list[str] = []
        seen: set[str] = set()
        for db_id in db_ids:
            lowered = db_id.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(configured.get(lowered, lowered))
        return normalized

    def _report_config_removal(
            self,
            db_id: str,
            removal: DatabaseConfigRemovalResult,
    ) -> None:
        for failure in removal.failures:
            self._update_output.error(
                'uninstall_ini_write_failed',
                f'Could not update {failure.source} for [{db_id}]: '
                f'{failure.error}',
            )
        if (
                removal.reappearance_reason
                == DatabaseReappearanceReason.NO_SOURCE
        ):
            self._update_output.warning(
                'uninstall_db_will_reappear',
                f"Database '{db_id}' has no downloader.ini section and will "
                'reappear on the next run.',
            )
        elif (
                removal.reappearance_reason
                == DatabaseReappearanceReason.NO_DATABASES_IN_BASE_INI
        ):
            self._update_output.warning(
                'uninstall_db_will_reappear',
                f"Database '{db_id}' will reappear on the next run because no databases remain in the base downloader.ini.",
            )
