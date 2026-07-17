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
from downloader.constants import CHECK_STATUS_FAILED, CHECK_STATUS_UPDATE_AVAILABLE, CHECK_STATUS_UP_TO_DATE, EXIT_CHECK_FAILED, \
    EXIT_CHECK_SUCCESS, EXIT_ERROR_WRONG_SETUP
from downloader.db_utils import DbSectionPackage, filter_db_sections, sorted_db_sections
from downloader.file_system import FileSystem
from downloader.local_repository import LocalRepository
from downloader.logger import Logger
from downloader.online_checker import CheckBox, OnlineChecker
from downloader.other import remove_run_signal
from downloader.update_output import UpdateOutput


class CheckService:
    def __init__(self, config: Config, online_checker: OnlineChecker, local_repository: LocalRepository, file_system: FileSystem, update_output: UpdateOutput, logger: Logger) -> None:
        self._config = config
        self._online_checker = online_checker
        self._local_repository = local_repository
        self._file_system = file_system
        self._update_output = update_output
        self._logger = logger

    def check_available_updates(self, db_ids: Optional[list[str]] = None) -> int:
        self._update_output.check_started()

        if db_ids:
            db_sections, invalid_db_ids = filter_db_sections(self._config, db_ids)
            if len(invalid_db_ids) > 0:
                self._update_output.error('check_invalid_db_ids', 'Invalid database ids: ' + ', '.join(invalid_db_ids))
                self._remove_run_signal()
                self._update_output.check_finished(EXIT_ERROR_WRONG_SETUP, CHECK_STATUS_FAILED)
                return EXIT_ERROR_WRONG_SETUP
        else:
            db_sections = sorted_db_sections(self._config)

        db_pkgs = [
            DbSectionPackage(db_id, section)
            for db_id, section in db_sections
        ]

        self._emit_file_space_state()
        check_box = self._online_checker.check_dbs(db_pkgs)
        self._emit_check_box(check_box)
        status = _check_status(check_box, len(db_pkgs))
        result = _check_result(status)
        self._remove_run_signal()
        self._update_output.check_finished(result, status)
        return result

    def _emit_file_space_state(self) -> None:
        previous_free_spaces = self._local_repository.load_previous_free_spaces()
        current_free_spaces = self._file_system.free_spaces()
        for path in sorted(set(previous_free_spaces.keys()) | set(current_free_spaces.keys())):
            self._update_output.check_file_space(
                path,
                previous_free_spaces.get(path, None),
                current_free_spaces.get(path, None),
            )

    def _emit_check_box(self, check_box: CheckBox) -> None:
        for db_id in sorted(check_box.up_to_date_dbs()):
            self._update_output.check_database_up_to_date(db_id)
        for db_id in sorted(check_box.need_update_dbs()):
            self._update_output.check_database_needs_update(db_id)
        for db_id in sorted(check_box.failed_dbs()):
            self._update_output.check_database_failed(db_id)
        for failure_id in sorted(check_box.fingerprint_failures()):
            self._update_output.check_fingerprint_failure(failure_id)

    def _remove_run_signal(self) -> None:
        remove_run_signal(self._file_system, self._logger)


def _check_status(check_box: CheckBox, db_count: int) -> str:
    if len(check_box.failed_dbs()) > 0 or len(check_box.fingerprint_failures()) > 0:
        return CHECK_STATUS_FAILED
    checked_dbs = len(check_box.up_to_date_dbs()) + len(check_box.need_update_dbs())
    if checked_dbs != db_count:
        return CHECK_STATUS_FAILED
    if len(check_box.need_update_dbs()) > 0:
        return CHECK_STATUS_UPDATE_AVAILABLE
    return CHECK_STATUS_UP_TO_DATE


def _check_result(status: str) -> int:
    if status == CHECK_STATUS_FAILED:
        return EXIT_CHECK_FAILED
    return EXIT_CHECK_SUCCESS
