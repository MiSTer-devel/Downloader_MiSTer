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

import os
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from downloader.config import Config
from downloader.constants import FILE_downloader_storage_fingerprints_json, FILE_downloader_storage_sigs_json, \
    FILE_PROP_ENTANGLEMENTS
from downloader.external_store_fingerprints import expected_external_store_fingerprints, \
    external_store_fingerprints_covered
from downloader.file_system import FileSystem
from downloader.local_repository import LocalRepository
from downloader.local_store_wrapper import LocalStore, LocalStoreWrapper, StoreWrapper
from downloader.logger import Logger
from downloader.path_package import PATH_TYPE_FILE, PATH_TYPE_FOLDER, PathPackage, PathType
from downloader.target_path_calculator import TargetPathsCalculator
from downloader.update_output import UpdateOutput
from downloader.waiter import Waiter


@dataclass
class _StoredPathPackage:
    store_path: str
    package: PathPackage


@dataclass
class _StoredFragmentPackages:
    drive: Optional[str]
    fragment: dict[str, Any]
    files: list[_StoredPathPackage]
    folders: list[_StoredPathPackage]


class OfflineUninstaller:
    def __init__(
            self,
            config: Config,
            file_system: FileSystem,
            local_repository: LocalRepository,
            waiter: Waiter,
            update_output: UpdateOutput,
            logger: Logger,
            target_paths_calculator: TargetPathsCalculator,
    ) -> None:
        self._config = config
        self._file_system = file_system
        self._local_repository = local_repository
        self._waiter = waiter
        self._update_output = update_output
        self._logger = logger
        self._target_paths_calculator = target_paths_calculator

    def uninstall_dbs(self, db_ids: list[str], force: bool) -> 'UninstallBox':
        box = UninstallBox()
        try:
            return self._uninstall_dbs(db_ids, force, box)
        except Exception as error:
            self._logger.debug(error)
            box.set_error(error)
            return box

    def _uninstall_dbs(
            self,
            db_ids: list[str],
            force: bool,
            box: 'UninstallBox',
    ) -> 'UninstallBox':
        wrapper = self._local_repository.load_store()
        local_store = wrapper.unwrap_local_store()
        configured_by_lower = {db_id.lower(): db_id for db_id in self._config['databases']}
        stored_by_lower = {db_id.lower(): db_id for db_id in local_store['dbs']}

        matched_ids: list[str] = []
        for requested_id in db_ids:
            lowered = requested_id.lower()
            actual_id = stored_by_lower.get(lowered, configured_by_lower.get(lowered))
            if actual_id is None:
                box.add_invalid_db_id(requested_id)
            else:
                matched_ids.append(actual_id)

        if box.invalid_db_ids():
            return box

        refused: set[str] = set()
        for db_id in matched_ids:
            if db_id not in local_store['dbs']:
                continue
            store = self._store_wrapper(wrapper, db_id)
            expected = expected_external_store_fingerprints(local_store['db_fingerprints'].get(db_id, {}))
            available = store.read_only().external_fragment_fingerprints()
            if force:
                self._warn_for_unverified_externals(db_id, expected, available)
                continue
            if expected is None:
                configured = db_id.lower() in configured_by_lower
                remedy = (
                    'Run the full updater once with all drives connected and rerun, or rerun with --force to skip verification.'
                    if configured else
                    'Rerun with --force to skip verification.'
                )
                self._refuse(box, db_id, remedy)
                refused.add(db_id)
            elif not external_store_fingerprints_covered(expected, available):
                self._refuse(
                    box,
                    db_id,
                    'If a drive is missing, reconnect it and rerun; or rerun with --force to accept unverified external content.',
                )
                refused.add(db_id)

        process_ids = [db_id for db_id in matched_ids if db_id not in refused]
        stored_fragments_by_db = self._stored_fragments_by_db(local_store, process_ids)
        total_bytes, total_files, reachable_fragments = self._reachable_totals(
            stored_fragments_by_db)
        self._update_output.uninstall_started(total_bytes, total_files, len(process_ids))

        changed = False
        claimants_by_kind_and_path = self._claimants_by_kind_and_path(
            wrapper, process_ids, stored_fragments_by_db)
        for db_id in process_ids:
            self._update_output.database_started(db_id)
            if db_id not in local_store['dbs']:
                box.add_uninstalled_db(db_id)
                continue

            changed = True
            failed, drive_disconnected = self._remove_db(
                db_id,
                box,
                local_store,
                stored_fragments_by_db[db_id],
                claimants_by_kind_and_path,
                reachable_fragments,
            )
            if failed:
                if drive_disconnected:
                    box.add_drive_disconnected_db(db_id)
                else:
                    box.add_failed_db(db_id)
            else:
                local_store['dbs'].pop(db_id, None)
                local_store['db_fingerprints'].pop(db_id, None)
                box.add_uninstalled_db(db_id)

        if changed:
            wrapper.mark_force_save()
            self._remove_legacy_fingerprint_files()
            if self._local_repository.save_store(wrapper) is not None:
                box.set_save_failed()
        return box

    @staticmethod
    def _store_wrapper(wrapper: LocalStoreWrapper, db_id: str) -> StoreWrapper:
        local_store = wrapper.unwrap_local_store()
        return StoreWrapper(
            local_store['dbs'][db_id],
            local_store['db_fingerprints'].get(db_id, {}),
            wrapper,
        )

    def _refuse(self, box: 'UninstallBox', db_id: str, remedy: str) -> None:
        message = f'Refused to uninstall [{db_id}]: external content could not be verified. {remedy}'
        box.add_refused_db(db_id, remedy)
        self._update_output.error('uninstall_db_refused', message)

    def _warn_for_unverified_externals(
            self, db_id: str, expected: Optional[list[str]], available: list[str]) -> None:
        if expected is None:
            self._update_output.warning(
                'uninstall_externals_unverified',
                f'WARNING! External fragment coverage is unknown for [{db_id}].',
            )
            return
        missing = sum((Counter(expected) - Counter(available)).values())
        if missing == 0:
            return
        noun = 'fragment' if missing == 1 else 'fragments'
        self._update_output.warning(
            'uninstall_externals_unverified',
            f'WARNING! {missing} expected external {noun} could not be verified for [{db_id}].',
        )

    def _reachable_totals(
            self,
            stored_fragments_by_db: dict[str, list[_StoredFragmentPackages]],
    ) -> tuple[int, int, set[tuple[str, Optional[str]]]]:
        total_bytes = 0
        total_files = 0
        reachable_fragments: set[tuple[str, Optional[str]]] = set()
        for db_id, fragments in stored_fragments_by_db.items():
            for fragment in fragments:
                if fragment.drive is not None and not self._file_system.is_folder(fragment.drive):
                    continue
                reachable_fragments.add((db_id, fragment.drive))
                for stored_path in fragment.files:
                    total_files += 1
                    total_bytes += stored_path.package.description.get('size', 0)
        return total_bytes, total_files, reachable_fragments

    def _remove_db(
            self,
            db_id: str,
            box: 'UninstallBox',
            local_store: LocalStore,
            fragments: list[_StoredFragmentPackages],
            claimants_by_kind_and_path: dict[str, dict[str, list[str]]],
            reachable_fragments: set[tuple[str, Optional[str]]],
    ) -> tuple[bool, bool]:
        store = local_store['dbs'][db_id]
        disconnected_drives: set[str] = set()
        other_failure = False

        for stored_fragment in fragments:
            drive = stored_fragment.drive
            fragment = stored_fragment.fragment
            if (db_id, drive) not in reachable_fragments:
                if drive is not None:
                    disconnected_drives.add(drive)
                continue
            if drive is not None and not self._file_system.is_folder(drive):
                disconnected_drives.add(drive)
                for stored_path in stored_fragment.files:
                    pkg = stored_path.package
                    self._update_output.file_skipped(
                        db_id, pkg.rel_path, pkg.description.get('size', 0), 'drive_disconnected')
                continue
            for stored_path in stored_fragment.files:
                pkg = stored_path.package
                size = pkg.description.get('size', 0)
                if drive in disconnected_drives:
                    self._update_output.file_skipped(
                        db_id, pkg.rel_path, size, 'drive_disconnected')
                    continue
                claimants = claimants_by_kind_and_path['files'].get(pkg.rel_path.lower(), [])
                if claimants:
                    fragment['files'].pop(stored_path.store_path, None)
                    self._update_output.warning(
                        'uninstall_file_kept',
                        f'Keeping {pkg.rel_path}: still claimed by [{", ".join(claimants)}].',
                    )
                    self._update_output.file_skipped(
                        db_id, pkg.rel_path, size, 'claimed')
                    continue
                if not self._file_system.is_file(pkg.full_path):
                    if drive is not None and not self._file_system.is_folder(drive):
                        disconnected_drives.add(drive)
                        self._update_output.file_skipped(
                            db_id, pkg.rel_path, size, 'drive_disconnected')
                        continue
                    fragment['files'].pop(stored_path.store_path, None)
                    self._update_output.file_skipped(
                        db_id, pkg.rel_path, size, 'missing')
                    continue
                error = self._unlink_with_retries(pkg.full_path, drive)
                if error is None:
                    fragment['files'].pop(stored_path.store_path, None)
                    tangles = pkg.description.get(FILE_PROP_ENTANGLEMENTS, [])
                    box.add_removed_file(size)
                    self._update_output.file_removed([db_id], pkg.rel_path, tangles, size)
                elif drive is not None and not self._file_system.is_folder(drive):
                    disconnected_drives.add(drive)
                    self._update_output.file_skipped(
                        db_id, pkg.rel_path, size, 'drive_disconnected')
                else:
                    other_failure = True
                    self._update_output.file_failed(
                        db_id, pkg.rel_path, size, str(error))

        for stored_fragment in fragments:
            drive = stored_fragment.drive
            fragment = stored_fragment.fragment
            if drive in disconnected_drives:
                continue
            folders = fragment.get('folders', {})
            for stored_path in sorted(
                    stored_fragment.folders,
                    key=lambda item: len(item.package.rel_path),
                    reverse=True,
            ):
                pkg = stored_path.package
                if pkg.rel_path.lower() in claimants_by_kind_and_path['folders']:
                    folders.pop(stored_path.store_path, None)
                    continue
                if drive is not None and not self._file_system.is_folder(drive):
                    disconnected_drives.add(drive)
                    break
                if self._file_system.is_folder(pkg.full_path) and not self._file_system.folder_has_items(pkg.full_path):
                    error = self._file_system.remove_folder(pkg.full_path)
                    if error is not None:
                        if drive is not None and not self._file_system.is_folder(drive):
                            disconnected_drives.add(drive)
                            break
                        other_failure = True
                        continue
                folders.pop(stored_path.store_path, None)

        has_leftovers = self._has_leftovers(store)
        failed = bool(disconnected_drives) or other_failure or has_leftovers
        only_drive_disconnected = bool(disconnected_drives) and not other_failure
        return failed, only_drive_disconnected

    @staticmethod
    def _claimants_by_kind_and_path(
            wrapper: LocalStoreWrapper,
            attempted_db_ids: list[str],
            stored_fragments_by_db: dict[str, list[_StoredFragmentPackages]],
    ) -> dict[str, dict[str, list[str]]]:
        local_store = wrapper.unwrap_local_store()
        candidates_by_kind: dict[str, set[str]] = {'files': set(), 'folders': set()}
        for fragments in stored_fragments_by_db.values():
            for fragment in fragments:
                candidates_by_kind['files'].update(
                    stored_path.package.rel_path.lower() for stored_path in fragment.files)
                candidates_by_kind['folders'].update(
                    stored_path.package.rel_path.lower() for stored_path in fragment.folders)

        claimants_by_kind_and_path: dict[str, dict[str, list[str]]] = {
            'files': {},
            'folders': {},
        }
        attempted_lower = {db_id.lower() for db_id in attempted_db_ids}
        for other_id, other_store in local_store['dbs'].items():
            if other_id.lower() in attempted_lower:
                continue
            other = StoreWrapper(
                other_store,
                local_store['db_fingerprints'].get(other_id, {}),
                None,
                readonly=True,
            )
            read_only = other.read_only()
            for kind, candidates in candidates_by_kind.items():
                for matching_path in read_only.matching_paths_ci(kind, candidates):
                    claimants_by_kind_and_path[kind].setdefault(
                        matching_path, []).append(other_id)
        return claimants_by_kind_and_path

    def _stored_fragments_by_db(
            self,
            local_store: LocalStore,
            db_ids: list[str],
    ) -> dict[str, list[_StoredFragmentPackages]]:
        return {
            db_id: self._stored_fragments(local_store['dbs'][db_id])
            for db_id in db_ids
            if db_id in local_store['dbs']
        }

    def _stored_fragments(self, store: dict[str, Any]) -> list[_StoredFragmentPackages]:
        fragments = [self._stored_fragment(None, store)]
        fragments.extend(
            self._stored_fragment(drive, fragment)
            for drive, fragment in store.get('external', {}).items()
        )
        return fragments

    def _stored_fragment(
            self,
            drive: Optional[str],
            fragment: dict[str, Any],
    ) -> _StoredFragmentPackages:
        return _StoredFragmentPackages(
            drive,
            fragment,
            self._stored_paths(fragment.get('files', {}), PATH_TYPE_FILE, drive),
            self._stored_paths(fragment.get('folders', {}), PATH_TYPE_FOLDER, drive),
        )

    def _stored_paths(
            self,
            paths: dict[str, dict[str, Any]],
            path_type: PathType,
            drive: Optional[str],
    ) -> list[_StoredPathPackage]:
        items = list(paths.items())
        packages = self._target_paths_calculator.create_stored_path_packages(
            items, path_type, drive)
        return [
            _StoredPathPackage(store_path, package)
            for (store_path, _), package in zip(items, packages)
        ]

    def _unlink_with_retries(self, path: str, drive: Optional[str]) -> Optional[Exception]:
        retries = self._config['downloader_retries']
        error: Optional[Exception] = None
        for attempt in range(retries + 1):
            error = self._file_system.unlink(path, verbose=False)
            if error is None or not self._file_system.is_file(path, use_cache=False):
                if drive is None or self._file_system.is_folder(drive):
                    return None
                return error
            if drive is not None and not self._file_system.is_folder(drive):
                return error
            if attempt < retries:
                self._waiter.sleep(1)
        return error

    @staticmethod
    def _has_leftovers(store: dict[str, Any]) -> bool:
        if store.get('files') or store.get('folders'):
            return True
        return any(
            fragment.get('files') or fragment.get('folders')
            for fragment in store.get('external', {}).values()
        )

    def _remove_legacy_fingerprint_files(self) -> None:
        for file_name in (FILE_downloader_storage_fingerprints_json, FILE_downloader_storage_sigs_json):
            path = os.path.join(self._config['base_system_path'], file_name)
            if not self._file_system.is_file(path):
                continue
            error = self._file_system.unlink(path, verbose=False)
            if error is not None:
                self._logger.debug('Could not remove store fingerprint file', path, error)


class UninstallBox:
    def __init__(self) -> None:
        self._invalid_db_ids: list[str] = []
        self._refused_dbs: list[tuple[str, str]] = []
        self._failed_db_ids: list[str] = []
        self._drive_disconnected_db_ids: list[str] = []
        self._uninstalled_db_ids: list[str] = []
        self._save_failed: bool = False
        self._removed_bytes: int = 0
        self._removed_files: int = 0
        self._error: Optional[Exception] = None

    def add_invalid_db_id(self, db_id: str) -> None:
        self._invalid_db_ids.append(db_id)

    def add_refused_db(self, db_id: str, reason: str) -> None:
        self._refused_dbs.append((db_id, reason))

    def add_failed_db(self, db_id: str) -> None:
        self._failed_db_ids.append(db_id)

    def add_drive_disconnected_db(self, db_id: str) -> None:
        self._failed_db_ids.append(db_id)
        self._drive_disconnected_db_ids.append(db_id)

    def add_uninstalled_db(self, db_id: str) -> None:
        self._uninstalled_db_ids.append(db_id)

    def add_removed_file(self, size: int) -> None:
        self._removed_files += 1
        self._removed_bytes += size

    def set_save_failed(self) -> None:
        self._save_failed = True

    def set_error(self, error: Exception) -> None:
        self._error = error

    def invalid_db_ids(self) -> list[str]: return list(self._invalid_db_ids)
    def refused_db_ids(self) -> list[str]: return [db_id for db_id, _reason in self._refused_dbs]
    def failed_db_ids(self) -> list[str]: return list(self._failed_db_ids)
    def drive_disconnected_db_ids(self) -> list[str]: return list(self._drive_disconnected_db_ids)
    def uninstalled_db_ids(self) -> list[str]: return list(self._uninstalled_db_ids)
    def save_failed(self) -> bool: return self._save_failed
    def removed_bytes(self) -> int: return self._removed_bytes
    def removed_files(self) -> int: return self._removed_files
    def error(self) -> Optional[Exception]: return self._error
