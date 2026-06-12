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


class SpyUpdateOutput:
    def __init__(self):
        self.events = []
        self.run_started_calls = []
        self.database_started_calls = []
        self.database_size_added_calls = []
        self.progress_line_calls = []
        self.work_in_progress_calls = []
        self.flush_pending_calls = []
        self.jobs_cancelled_calls = []
        self.file_started_calls = []
        self.file_completed_calls = []
        self.file_removed_calls = []
        self.file_failed_calls = []
        self.file_duplicated_calls = []
        self.not_overwritten_calls = []
        self.full_partition_calls = []
        self.reboot_required_calls = []
        self.linux_update_started_calls = []
        self.linux_update_phase_calls = []
        self.linux_update_failed_calls = []
        self.linux_update_completed_calls = []
        self.warning_calls = []
        self.error_calls = []
        self.database_failed_calls = []
        self.zip_failed_calls = []
        self.folder_failed_calls = []
        self.run_finished_calls = []

    def run_started(self, version: str, commit: str) -> None:
        self.run_started_calls.append((version, commit))
        self.events.append(('run_start', version, commit))

    def database_started(self, db_id: str) -> None:
        self.database_started_calls.append((db_id,))
        self.events.append(('db_start', db_id))

    def database_size_added(self, db_id: str, bytes_added: int, files_added: int, source: str, zip_id: str = '') -> None:
        self.database_size_added_calls.append((db_id, bytes_added, files_added, source, zip_id))
        self.events.append(('db_size_add', db_id, bytes_added, files_added, source, zip_id))

    def progress_line(self, line: str) -> None:
        self.progress_line_calls.append((line,))
        self.events.append(('progress_line', line))

    def work_in_progress(self) -> None:
        self.work_in_progress_calls.append(())
        self.events.append(('work_in_progress',))

    def flush_pending(self) -> None:
        self.flush_pending_calls.append(())
        self.events.append(('flush_pending',))

    def jobs_cancelled(self, count: int) -> None:
        self.jobs_cancelled_calls.append((count,))
        self.events.append(('jobs_cancelled', count))

    def file_started(self, db_id: str, path: str, size: int, tangles: list[str]) -> None:
        self.file_started_calls.append((db_id, path, size, tangles))
        self.events.append(('file_start', db_id, path, size, tangles))

    def file_completed(self, db_id: str, path: str, size: int, already_exists: bool, zip_id: str = '', reboot: bool = False) -> None:
        self.file_completed_calls.append((db_id, path, size, already_exists, zip_id, reboot))
        self.events.append(('file_done', db_id, path, size, already_exists, zip_id, reboot))

    def file_removed(self, dbs: list[str], path: str, tangles: list[str]) -> None:
        self.file_removed_calls.append((dbs, path, tangles))
        self.events.append(('file_remove', dbs, path, tangles))

    def file_failed(self, db_id: str, path: str, size: int, reason: str) -> None:
        self.file_failed_calls.append((db_id, path, size, reason))
        self.events.append(('file_fail', db_id, path, size, reason))

    def file_duplicated(self, dbs: list[str], path: str, used_db_id: str) -> None:
        self.file_duplicated_calls.append((dbs, path, used_db_id))
        self.events.append(('file_duplicate', dbs, path, used_db_id))

    def not_overwritten(self, db_id: str, path: str) -> None:
        self.not_overwritten_calls.append((db_id, path))
        self.events.append(('not_overwritten', db_id, path))

    def full_partition(self, path: str, bytes_needed: int) -> None:
        self.full_partition_calls.append((path, bytes_needed))
        self.events.append(('full_partition', path, bytes_needed))

    def reboot_required(self, kind: str) -> None:
        self.reboot_required_calls.append((kind,))
        self.events.append(('reboot_required', kind))

    def linux_update_started(self, db_id: str, current_version: str, new_version: str, url: str) -> None:
        self.linux_update_started_calls.append((db_id, current_version, new_version, url))
        self.events.append(('linux_start', db_id, current_version, new_version, url))

    def linux_update_phase(self, phase: str) -> None:
        self.linux_update_phase_calls.append((phase,))
        self.events.append(('linux_phase', phase))

    def linux_update_failed(self, phase: str, message: str = '') -> None:
        self.linux_update_failed_calls.append((phase, message))
        self.events.append(('linux_fail', phase, message))

    def linux_update_completed(self) -> None:
        self.linux_update_completed_calls.append(())
        self.events.append(('linux_done',))

    def warning(self, code: str, message: str) -> None:
        self.warning_calls.append((code, message))
        self.events.append(('warning', code, message))

    def error(self, code: str, message: str = '') -> None:
        self.error_calls.append((code, message))
        self.events.append(('error', code, message))

    def database_failed(self, db_id: str) -> None:
        self.database_failed_calls.append((db_id,))
        self.events.append(('db_fail', db_id))

    def zip_failed(self, db_id: str, zip_id: str) -> None:
        self.zip_failed_calls.append((db_id, zip_id))
        self.events.append(('zip_fail', db_id, zip_id))

    def folder_failed(self, path: str) -> None:
        self.folder_failed_calls.append((path,))
        self.events.append(('folder_fail', path))

    def run_finished(self, exit_code: int) -> None:
        self.run_finished_calls.append((exit_code,))
        self.events.append(('run_finish', exit_code))
