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

import sys
import time
from typing import Optional, Protocol, TextIO, Union

from downloader.config import ConfigDatabaseSection
from downloader.constants import DOWNLOADER_OUTPUT_DLP1_LTSV
from downloader.logger import Logger
from downloader.other import screen_columns

ConfiguredDatabase = tuple[str, ConfigDatabaseSection]


class UpdateOutput(Protocol):
    def run_started(self, version: str, commit: str) -> None: pass
    def database_started(self, db_id: str) -> None: pass
    def database_size_added(self, db_id: str, bytes_added: int, files_added: int, source: str, zip_id: str = '') -> None: pass
    def progress_line(self, line: str) -> None: pass
    def work_in_progress(self) -> None: pass
    def flush_pending(self) -> None: pass
    def jobs_cancelled(self, count: int) -> None: pass
    def file_started(self, db_id: str, path: str, size: int, tangles: list[str]) -> None: pass
    def file_completed(self, db_id: str, path: str, size: int, already_exists: bool, zip_id: str = '', reboot: bool = False) -> None: pass
    def file_removed(self, dbs: list[str], path: str, tangles: list[str], size: int) -> None: pass
    def file_failed(self, db_id: str, path: str, size: int, reason: str) -> None: pass
    # dbs are all the databases declaring the path; used_db_id is the one whose copy is used, the others were skipped as duplicates.
    def file_duplicated(self, dbs: list[str], path: str, used_db_id: str) -> None: pass
    def not_overwritten(self, db_id: str, path: str) -> None: pass
    def full_partition(self, path: str, bytes_needed: int) -> None: pass
    def reboot_required(self, kind: str) -> None: pass
    # url is the SD installer recovery url, needed if the flash phase gets interrupted.
    def linux_update_started(self, db_id: str, current_version: str, new_version: str, url: str) -> None: pass
    # phase is one of: 'fetch_image', 'fetch_7z', 'extract', 'user_files', 'flash'
    def linux_update_phase(self, phase: str) -> None: pass
    def linux_update_failed(self, phase: str, message: str = '') -> None: pass
    def linux_update_completed(self) -> None: pass
    def warning(self, code: str, message: str) -> None: pass
    def error(self, code: str, message: str = '') -> None: pass
    def database_failed(self, db_id: str) -> None: pass
    def zip_failed(self, db_id: str, zip_id: str) -> None: pass
    def folder_failed(self, path: str) -> None: pass
    def run_finished(self, exit_code: int) -> None: pass
    def check_started(self) -> None: pass
    def check_file_space(self, path: str, previous: Optional[int], current: Optional[int]) -> None: pass
    def check_database_up_to_date(self, db_id: str) -> None: pass
    def check_database_needs_update(self, db_id: str) -> None: pass
    def check_database_failed(self, db_id: str) -> None: pass
    def check_fingerprint_failure(self, failure_id: str) -> None: pass
    def check_finished(self, exit_code: int, status: str) -> None: pass
    def configured_databases(self, dbs: list[ConfiguredDatabase]) -> None: pass


class NoopUpdateOutput(UpdateOutput):
    def run_started(self, version: str, commit: str) -> None: pass
    def database_started(self, db_id: str) -> None: pass
    def database_size_added(self, db_id: str, bytes_added: int, files_added: int, source: str, zip_id: str = '') -> None: pass
    def progress_line(self, line: str) -> None: pass
    def work_in_progress(self) -> None: pass
    def flush_pending(self) -> None: pass
    def jobs_cancelled(self, count: int) -> None: pass
    def file_started(self, db_id: str, path: str, size: int, tangles: list[str]) -> None: pass
    def file_completed(self, db_id: str, path: str, size: int, already_exists: bool, zip_id: str = '', reboot: bool = False) -> None: pass
    def file_removed(self, dbs: list[str], path: str, tangles: list[str], size: int) -> None: pass
    def file_failed(self, db_id: str, path: str, size: int, reason: str) -> None: pass
    def file_duplicated(self, dbs: list[str], path: str, used_db_id: str) -> None: pass
    def not_overwritten(self, db_id: str, path: str) -> None: pass
    def full_partition(self, path: str, bytes_needed: int) -> None: pass
    def reboot_required(self, kind: str) -> None: pass
    def linux_update_started(self, db_id: str, current_version: str, new_version: str, url: str) -> None: pass
    def linux_update_phase(self, phase: str) -> None: pass
    def linux_update_failed(self, phase: str, message: str = '') -> None: pass
    def linux_update_completed(self) -> None: pass
    def warning(self, code: str, message: str) -> None: pass
    def error(self, code: str, message: str = '') -> None: pass
    def database_failed(self, db_id: str) -> None: pass
    def zip_failed(self, db_id: str, zip_id: str) -> None: pass
    def folder_failed(self, path: str) -> None: pass
    def run_finished(self, exit_code: int) -> None: pass
    def check_started(self) -> None: pass
    def check_file_space(self, path: str, previous: Optional[int], current: Optional[int]) -> None: pass
    def check_database_up_to_date(self, db_id: str) -> None: pass
    def check_database_needs_update(self, db_id: str) -> None: pass
    def check_database_failed(self, db_id: str) -> None: pass
    def check_fingerprint_failure(self, failure_id: str) -> None: pass
    def check_finished(self, exit_code: int, status: str) -> None: pass
    def configured_databases(self, dbs: list[ConfiguredDatabase]) -> None: pass


class HumanUpdateOutput(UpdateOutput):
    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._check_time: float = 0
        self._needs_newline: bool = False
        self._need_clear_header: bool = False
        self._symbols: list[str] = []
        self._columns: int = screen_columns()
        self._linux_recovery_url: str = ''

    def run_started(self, version: str, commit: str) -> None:
        self._logger.print('START!')
        self._logger.print()

    def database_started(self, db_id: str) -> None:
        self._print_symbols()
        first_line = '\n' if self._needs_newline else ''
        self._needs_newline = False
        self._logger.print(
            first_line +
            '#' * self._columns + '\n' +
            f'SECTION: {db_id}\n'
        )
        self._need_clear_header = True
        self._check_time = time.monotonic() + 2.0

    def database_size_added(self, db_id: str, bytes_added: int, files_added: int, source: str, zip_id: str = '') -> None:
        pass

    def progress_line(self, line: str) -> None:
        self._print_line(line)
        self._check_time = time.monotonic() + 2.0

    def work_in_progress(self) -> None:
        now = time.monotonic()
        if self._check_time < now:
            self._symbols.append('*')
            self._print_symbols()

    def flush_pending(self) -> None:
        self._print_symbols()
        if self._needs_newline:
            self._logger.print()
            self._needs_newline = False

    def jobs_cancelled(self, count: int) -> None:
        self._logger.print(f"Cancelled {count} jobs.")

    def file_started(self, db_id: str, path: str, size: int, tangles: list[str]) -> None:
        self._print_line(path)
        self._check_time = time.monotonic() + 2.0

    def file_completed(self, db_id: str, path: str, size: int, already_exists: bool, zip_id: str = '', reboot: bool = False) -> None:
        self._symbols.append('.')
        if self._needs_newline or self._check_time < time.monotonic():
            self._print_symbols()

    def file_removed(self, dbs: list[str], path: str, tangles: list[str], size: int) -> None:
        self._print_line(f'Removing {path}')

    def file_failed(self, db_id: str, path: str, size: int, reason: str) -> None:
        self._symbols.append('~')
        self._print_symbols()

    def file_duplicated(self, dbs: list[str], path: str, used_db_id: str) -> None:
        self._print_line(f'DUPLICATED: {path} in [{", ".join(dbs)}] [using {used_db_id} instead]')

    def not_overwritten(self, db_id: str, path: str) -> None:
        pass

    def full_partition(self, path: str, bytes_needed: int) -> None:
        pass

    def reboot_required(self, kind: str) -> None:
        pass

    def linux_update_started(self, db_id: str, current_version: str, new_version: str, url: str) -> None:
        self._linux_recovery_url = url
        self._print_line(f'Linux will be updated from {db_id}:')
        self._logger.print(f'Current linux version -> {current_version}')
        self._logger.print(f'Latest linux version -> {new_version}')
        self._logger.print()

    def linux_update_phase(self, phase: str) -> None:
        if phase == 'fetch_image':
            self._print_line('Fetching the new Linux image... (this can take a while)')
        elif phase == 'fetch_7z':
            self._print_line('Fetching 7za.gz file...')
        elif phase == 'user_files':
            self._print_line('Restoring user Linux configuration files:')
        elif phase == 'flash':
            self._print_line('')
            self._logger.print("======================================================================================")
            self._logger.print("Hold your breath: updating the Kernel, the Linux filesystem, the bootloader and stuff.")
            self._logger.print("Stopping this will make your SD unbootable!")
            self._logger.print()
            self._logger.print("If something goes wrong, please download the SD Installer from")
            self._logger.print(self._linux_recovery_url)
            self._logger.print("and copy the content of the files/linux/ directory in the linux directory of the SD.")
            self._logger.print("Reflash the bootloader with the SD Installer if needed.")
            self._logger.print("======================================================================================")
            self._logger.print(flush=True)

    def linux_update_failed(self, phase: str, message: str = '') -> None:
        errors = {
            'fetch_image': 'ERROR! Could not fetch the Linux image.',
            'fetch_7z': 'ERROR! Could not install 7z.',
            'extract': 'ERROR! Could not uncompress the linux installer.',
            'user_files': 'ERROR! Could not restore user Linux configuration files.',
            'flash': 'ERROR! Something went wrong during the Linux update, try again later.',
        }
        self._print_line(errors.get(phase, f'ERROR! Linux update failed during {phase}.'))
        if message:
            self._logger.print(message)
        self._logger.print()

    def linux_update_completed(self) -> None:
        pass

    def warning(self, code: str, message: str) -> None:
        self._logger.print(message)

    def error(self, code: str, message: str = '') -> None:
        if message:
            self._logger.print(f'ERROR: {message}')

    def database_failed(self, db_id: str) -> None:
        pass

    def zip_failed(self, db_id: str, zip_id: str) -> None:
        pass

    def folder_failed(self, path: str) -> None:
        pass

    def run_finished(self, exit_code: int) -> None:
        pass

    def check_started(self) -> None:
        self._logger.print('Checking for available updates...')

    def check_file_space(self, path: str, previous: Optional[int], current: Optional[int]) -> None:
        previous_text = 'unknown' if previous is None else str(previous)
        current_text = 'unknown' if current is None else str(current)
        self._logger.print(f'Free space: {path}: {previous_text} -> {current_text}')

    def check_database_up_to_date(self, db_id: str) -> None:
        self._logger.print(f'Up-to-date: [{db_id}]')

    def check_database_needs_update(self, db_id: str) -> None:
        self._logger.print(f'Update available: [{db_id}]')

    def check_database_failed(self, db_id: str) -> None:
        self._logger.print(f'Check failed: [{db_id}]')

    def check_fingerprint_failure(self, failure_id: str) -> None:
        self._logger.print(f'Check failed: {failure_id}')

    def check_finished(self, exit_code: int, status: str) -> None:
        self._logger.print(f'Check finished with code {exit_code}.')
        self._logger.print(status)

    def configured_databases(self, dbs: list[ConfiguredDatabase]) -> None:
        for db_id, section in dbs:
            fields = _configured_db_extra_fields(section)
            option_text = ''.join(f' {key}={value}' for key, value in fields.items())
            self._logger.print(f"{db_id} {section['db_url']}{option_text}")

    def _print_symbols(self) -> None:
        if len(self._symbols) == 0:
            return

        last_is_asterisk = self._symbols[-1] == '*'

        self._logger.print(('\n' if self._need_clear_header else '') + ''.join(self._symbols), end='')
        self._symbols.clear()

        self._need_clear_header = False
        self._needs_newline = True
        self._check_time = time.monotonic() + (1.0 if last_is_asterisk else 2.0)

    def _print_line(self, line: str) -> None:
        if self._need_clear_header:
            line = '\n' + line
        if self._needs_newline:
            line = '\n' + line
        self._logger.print(line)
        self._needs_newline = False
        self._need_clear_header = False


class LtsvUpdateOutput(UpdateOutput):
    def __init__(self, logger: Logger, stream: Optional[TextIO] = None) -> None:
        self._stream = sys.stdout if stream is None else stream
        self._human_output = HumanUpdateOutput(logger)

    def run_started(self, version: str, commit: str) -> None:
        self._emit('run_start', version=version, commit=commit)
        self._human_output.run_started(version, commit)

    def database_started(self, db_id: str) -> None:
        self._emit('db_start', db=db_id)
        self._human_output.database_started(db_id)

    def database_size_added(self, db_id: str, bytes_added: int, files_added: int, source: str, zip_id: str = '') -> None:
        fields: dict[str, Union[str, int]] = {'db': db_id, 'bytes': bytes_added, 'files': files_added, 'src': source}
        if zip_id:
            fields['zip'] = zip_id
        self._emit('db_size_add', **fields)

    def progress_line(self, line: str) -> None:
        self._human_output.progress_line(line)

    def work_in_progress(self) -> None:
        self._human_output.work_in_progress()

    def flush_pending(self) -> None:
        self._human_output.flush_pending()

    def jobs_cancelled(self, count: int) -> None:
        self._human_output.jobs_cancelled(count)

    def file_started(self, db_id: str, path: str, size: int, tangles: list[str]) -> None:
        tangles = _valid_string_list(tangles)
        fields: dict[str, Union[str, int]] = {
            'db': db_id,
            'size': size,
            'path': path,
        }
        if len(tangles) > 0:
            fields['tangle'] = ','.join(tangles)
        self._emit('file_start', **fields)
        self._human_output.file_started(db_id, path, size, tangles)

    def file_completed(self, db_id: str, path: str, size: int, already_exists: bool, zip_id: str = '', reboot: bool = False) -> None:
        fields: dict[str, Union[str, int]] = {'db': db_id, 'size': size, 'path': path}
        fields['target'] = 'existing' if already_exists else 'new'
        if zip_id:
            fields['zip'] = zip_id
        if reboot:
            fields['reboot'] = 'true'
        self._emit('file_done', **fields)
        self._human_output.file_completed(db_id, path, size, already_exists, zip_id, reboot)

    def file_removed(self, dbs: list[str], path: str, tangles: list[str], size: int) -> None:
        dbs = sorted(_valid_string_list(dbs))
        tangles = _valid_string_list(tangles)
        fields: dict[str, Union[str, int]] = {'dbs': ','.join(dbs), 'path': path}
        if len(tangles) > 0:
            fields['tangle'] = ','.join(tangles)
        self._emit('file_remove', **fields)
        self._human_output.file_removed(dbs, path, tangles, size)

    def file_failed(self, db_id: str, path: str, size: int, reason: str) -> None:
        self._emit('file_fail', db=db_id, size=size, path=path, reason=reason)
        self._human_output.file_failed(db_id, path, size, reason)

    def file_duplicated(self, dbs: list[str], path: str, used_db_id: str) -> None:
        dbs = sorted(_valid_string_list(dbs))
        self._emit('file_duplicate', dbs=','.join(dbs), path=path, used=used_db_id)
        self._human_output.file_duplicated(dbs, path, used_db_id)

    def not_overwritten(self, db_id: str, path: str) -> None:
        self._emit('not_overwritten', db=db_id, path=path)

    def full_partition(self, path: str, bytes_needed: int) -> None:
        self._emit('full_partition', path=path, bytes=bytes_needed)

    def reboot_required(self, kind: str) -> None:
        self._emit('reboot_required', kind=kind)

    def linux_update_started(self, db_id: str, current_version: str, new_version: str, url: str) -> None:
        self._emit('linux_start', db=db_id, current=current_version, new=new_version, url=url)
        self._human_output.linux_update_started(db_id, current_version, new_version, url)

    def linux_update_phase(self, phase: str) -> None:
        self._emit('linux_phase', phase=phase)
        self._human_output.linux_update_phase(phase)

    def linux_update_failed(self, phase: str, message: str = '') -> None:
        fields: dict[str, Union[str, int]] = {'phase': phase}
        if message:
            fields['message'] = message
        self._emit('linux_fail', **fields)
        self._human_output.linux_update_failed(phase, message)

    def linux_update_completed(self) -> None:
        self._emit('linux_done')
        self._human_output.linux_update_completed()

    def warning(self, code: str, message: str) -> None:
        self._emit('warning', code=code, message=message)
        self._human_output.warning(code, message)

    def error(self, code: str, message: str = '') -> None:
        fields: dict[str, Union[str, int]] = {'code': code}
        if message:
            fields['message'] = message
        self._emit('error', **fields)
        self._human_output.error(code, message)

    def database_failed(self, db_id: str) -> None:
        self._emit('db_fail', db=db_id)

    def zip_failed(self, db_id: str, zip_id: str) -> None:
        self._emit('zip_fail', db=db_id, zip=zip_id)

    def folder_failed(self, path: str) -> None:
        self._emit('folder_fail', path=path)

    def run_finished(self, exit_code: int) -> None:
        self._emit('run_finish', code=exit_code)

    def check_started(self) -> None:
        self._emit('check_start')
        self._human_output.check_started()

    def check_file_space(self, path: str, previous: Optional[int], current: Optional[int]) -> None:
        fields: dict[str, Union[str, int]] = {
            'path': path,
            'previous': 'unknown' if previous is None else previous,
            'current': 'unknown' if current is None else current,
        }
        if previous is not None and current is not None:
            fields['delta'] = current - previous
        self._emit('check_file_space', **fields)
        self._human_output.check_file_space(path, previous, current)

    def check_database_up_to_date(self, db_id: str) -> None:
        self._emit('check_db_up_to_date', db=db_id)
        self._human_output.check_database_up_to_date(db_id)

    def check_database_needs_update(self, db_id: str) -> None:
        self._emit('check_db_need_update', db=db_id)
        self._human_output.check_database_needs_update(db_id)

    def check_database_failed(self, db_id: str) -> None:
        self._emit('check_db_fail', db=db_id)
        self._human_output.check_database_failed(db_id)

    def check_fingerprint_failure(self, failure_id: str) -> None:
        self._emit('check_fingerprint_fail', id=failure_id)
        self._human_output.check_fingerprint_failure(failure_id)

    def check_finished(self, exit_code: int, status: str) -> None:
        self._emit('check_finish', code=exit_code, status=status)
        self._human_output.check_finished(exit_code, status)

    def configured_databases(self, dbs: list[ConfiguredDatabase]) -> None:
        for db_id, section in dbs:
            fields: dict[str, Union[str, int]] = {'db': db_id, 'url': section['db_url']}
            fields.update(_configured_db_extra_fields(section))
            self._emit('configured_db', **fields)

    def _emit(self, event: str, **fields: Union[str, int]) -> None:
        line = ['DLP1', f'event:{_sanitize(event)}']
        for key, value in fields.items():
            line.append(f'{_sanitize(key)}:{_sanitize(str(value))}')
        print('\t'.join(line), file=self._stream, flush=True)


def update_output_for_mode(mode: str, logger: Logger) -> UpdateOutput:
    return LtsvUpdateOutput(logger) if mode.lower() == DOWNLOADER_OUTPUT_DLP1_LTSV else HumanUpdateOutput(logger)


def _sanitize(value: str) -> str:
    return value.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')


def _valid_string_list(values: object) -> list[str]:
    return [value for value in values if isinstance(value, str)] if isinstance(values, list) else []


def _configured_db_extra_fields(section: ConfigDatabaseSection) -> dict[str, str]:
    fields: dict[str, str] = {}
    if 'description' in section:
        fields['description'] = section['description']

    fields.update(_db_options_fields(section))
    return fields


def _db_options_fields(section: ConfigDatabaseSection) -> dict[str, str]:
    if 'options' not in section:
        return {}

    props = section['options'].unwrap_props()
    if not isinstance(props, dict):
        return {}

    return {str(key): str(value) for key, value in sorted(props.items())}
