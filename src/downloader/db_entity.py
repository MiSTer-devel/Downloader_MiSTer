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

import ipaddress
from typing import Dict, Any, Final, List, Optional
from urllib.parse import urlparse

from downloader.constants import FILE_MiSTer, FILE_menu_rbf, FILE_MiSTer_ini, FILE_MiSTer_alt_ini, \
    FILE_downloader_launcher_script, FILE_MiSTer_alt_3_ini, FILE_MiSTer_alt_1_ini, FILE_MiSTer_alt_2_ini, \
    FILE_MiSTer_new, FOLDER_linux, FOLDER_saves, FOLDER_savestates, FOLDER_screenshots, FILE_PDFViewer, FILE_lesskey, \
    FILE_glow, FOLDER_gamecontrollerdb, FILE_gamecontrollerdb, DISTRIBUTION_MISTER_DB_ID, FILE_gamecontrollerdb_user, \
    FILE_yc_txt
from downloader.db_options import DbOptions
from downloader.other import test_only
from downloader.path_package import PathPackage


class DbEntity:
    def __init__(self, db_raw: Any, section: str) -> None:
        if not isinstance(db_raw, dict):
            raise DbEntityValidationException(f'ERROR: Database "{section}" has improper format. The database maintainer should fix this.')

        if 'db_id' not in db_raw: raise DbEntityValidationException(f'ERROR: Database "{section}" needs a "db_id" field. The database maintainer should fix this.')
        if 'files' not in db_raw: raise DbEntityValidationException(f'ERROR: Database "{section}" needs a "files" field. The database maintainer should fix this.')
        if 'folders' not in db_raw: raise DbEntityValidationException(f'ERROR: Database "{section}" needs a "folders" field. The database maintainer should fix this.')
        if 'timestamp' not in db_raw: raise DbEntityValidationException(f'ERROR: Database "{section}" needs a "timestamp" field. The database maintainer should fix this.')

        self.db_id: str = db_raw['db_id'].lower()
        if self.db_id != section.lower(): raise DbEntityValidationException(f'ERROR: Section "{section}" does not match database id "{self.db_id}". Fix your INI file.')
        self.timestamp: int = db_raw['timestamp']
        if not isinstance(self.timestamp, int): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "timestamp" field. The database maintainer should fix this.')
        self.files: Dict[str, Any] = db_raw['files']
        if not isinstance(self.files, dict): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "files" field. The database maintainer should fix this.')
        self.folders: Dict[str, Any] = db_raw['folders']
        if not isinstance(self.folders, dict): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "folders" field. The database maintainer should fix this.')

        self.zips: Dict[str, Any] = db_raw.get('zips', {})
        if not isinstance(self.zips, dict): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "zips" field. The database maintainer should fix this.')
        self.base_files_url: str = db_raw.get('base_files_url', '')
        if not isinstance(self.base_files_url, str): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "base_files_url" field. The database maintainer should fix this.')
        self.tag_dictionary: Dict[str, int] = db_raw.get('tag_dictionary', {})
        if not isinstance(self.tag_dictionary, dict): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "tag_dictionary" field. The database maintainer should fix this.')
        self.linux: Optional[Dict[str, Any]] = db_raw.get('linux', None)
        if self.linux is not None and not isinstance(self.linux, dict): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "linux" field. The database maintainer should fix this.')
        self.header: List[str] = db_raw.get('header', [])
        if not isinstance(self.header, list): raise DbEntityValidationException(f'ERROR: Database "{section}" needs a valid "header" field. The database maintainer should fix this.')
        self.default_options: DbOptions = DbOptions(db_raw.get('default_options', None) or {})

    @property
    @test_only
    def testable(self) -> dict[str, Any]:  # pragma: no cover
        result = self.__dict__.copy()
        result['default_options'] = result['default_options'].testable
        if result['linux'] is None:
            result.pop('linux')
        if result['header'] is None:
            result.pop('header')
        return result

def check_zip(desc: dict[str, Any], db_id: str, zip_id: str) -> None:
    if 'kind' not in desc or desc['kind'] not in ('extract_all_contents', 'extract_single_files'):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. It needs to contain a valid "kind" field. The database maintainer should fix this.')
    if 'description' not in desc or not isinstance(desc['description'], str):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. It needs to contain a valid "description" field. The database maintainer should fix this.')
    if 'contents_file' not in desc or not isinstance(desc['contents_file'], dict):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. It needs to contain a valid "contents_file" field. The database maintainer should fix this.')
    if ('internal_summary' not in desc or not isinstance(desc['internal_summary'], dict)) and ('summary_file' not in desc or not isinstance(desc['summary_file'], dict)):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. It needs to contain a valid summary field. The database maintainer should fix this.')

    if 'hash' not in desc['contents_file'] or not isinstance(desc['contents_file']['hash'], str):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Contents file needs a valid hash. The database maintainer should fix this.')
    if 'size' not in desc['contents_file'] or not isinstance(desc['contents_file']['size'], int):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Contents file needs a valid size. The database maintainer should fix this.')
    if 'url' not in desc['contents_file'] or not is_url_valid(desc['contents_file']['url']):
        raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Contents file needs a valid url. The database maintainer should fix this.')

    if 'internal_summary' in desc:
        check_zip_summary(desc['internal_summary'], db_id, zip_id)
    else:
        if 'hash' not in desc['summary_file'] or not isinstance(desc['summary_file']['hash'], str):
            raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Summary file needs a valid hash. The database maintainer should fix this.')
        if 'size' not in desc['summary_file'] or not isinstance(desc['summary_file']['size'], int):
            raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Summary file needs a valid size. The database maintainer should fix this.')
        if 'url' not in desc['summary_file'] or not is_url_valid(desc['summary_file']['url']):
            raise DbEntityValidationException(f'ERROR: Invalid zip "{zip_id}" for database: {db_id}. Summary file needs a valid url. The database maintainer should fix this.')

def check_zip_summary(summary: dict[str, Any], db_id: str, zip_id: str) -> None:
    if 'files' not in summary or not isinstance(summary['files'], dict):
        raise DbEntityValidationException(f'ERROR: Invalid zip summary "{zip_id}" for database: {db_id}. Summary needs valid files dictionary. The database maintainer should fix this.')
    if 'folders' not in summary or not isinstance(summary['folders'], dict):
        raise DbEntityValidationException(f'ERROR: Invalid zip summary "{zip_id}" for database: {db_id}. Summary needs valid folders dictionary. The database maintainer should fix this.')

def check_no_url_files(files: list[PathPackage], db_id: str) -> None:
    if len(files) == 0: return

    for file_pkg in files:
        file_path, file_description = file_pkg.rel_path, file_pkg.description
        parts = _validate_and_extract_parts_from_path(db_id, file_path)
        if parts[0] in folders_with_non_overridable_files and file_description.get('overwrite', True):
            raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. Can not override in that folder. The database maintainer should fix this.')

        if 'hash' not in file_description or not isinstance(file_description['hash'], str): raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. File needs a valid hash. The database maintainer should fix this.')
        if 'size' not in file_description or not isinstance(file_description['size'], int): raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. File needs a valid size. The database maintainer should fix this.')

def check_file(file_pkg: PathPackage, db_id: str, url: Optional[str], /) -> None:
    file_path, file_description = file_pkg.rel_path, file_pkg.description
    if not is_url_valid(url or file_description.get('url', None)):
        raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. Invalid url "{url}". The database maintainer should fix this.')

    parts = _validate_and_extract_parts_from_path(db_id, file_path)
    if parts[0] in folders_with_non_overridable_files and file_description.get('overwrite', True):
        raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. Can not override in that folder. The database maintainer should fix this.')

    if 'hash' not in file_description or not isinstance(file_description['hash'], str): raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. File needs a valid hash. The database maintainer should fix this.')
    if 'size' not in file_description or not isinstance(file_description['size'], int): raise DbEntityValidationException(f'ERROR: Invalid file "{file_path}" for database: {db_id}. File needs a valid size. The database maintainer should fix this.')

def is_url_valid(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if any(c in url for c in ("\r", "\n")):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() == "localhost":
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return False
        except ValueError:
            pass
        return True
    except:
        return False

def check_folders(folders: dict[str, Any], db_id: str) -> None:
    if len(folders) == 0: return

    for folder_path in folders:
        _validate_and_extract_parts_from_path(db_id, folder_path)

def fix_folders(folders: dict[str, Any]) -> None:
    if len(folders) == 0: return

    rename_folders = []
    for folder_path, folder_description in folders.items():
        if folder_path.endswith('/'):
            rename_folders.append((folder_path, folder_description))

    for folder_path, folder_description in rename_folders:
        folders[folder_path[:-1]] = folder_description
        folders.pop(folder_path)

def _validate_and_extract_parts_from_path(db_id: str, path: str) -> list[str]:
    if not isinstance(path, str):
        raise DbEntityValidationException(f'ERROR: Invalid file "{path}" for database: {db_id}. Path should be a string. The database maintainer should fix this.')

    if path == '' or path[0] == '/' or path[0] == '.' or path[0] == '\\':
        raise DbEntityValidationException(f'ERROR: Invalid file "{path}" for database: {db_id}. Path should be valid. The database maintainer should fix this.')

    lower_path = path.lower()
    parts = lower_path.split('/')

    if lower_path in exceptional_paths:
        return parts

    if db_id == DISTRIBUTION_MISTER_DB_ID and lower_path in distribution_mister_exceptional_paths:
        return parts

    if lower_path in invalid_paths:
        raise DbEntityValidationException(f'ERROR: Invalid file "{path}" for database: {db_id}. Path should not be illegal. The database maintainer should fix this.')

    if db_id != DISTRIBUTION_MISTER_DB_ID and lower_path in no_distribution_mister_invalid_paths:
        raise DbEntityValidationException(f'ERROR: Invalid file "{path}" for database: {db_id}. Path should only valid for distribution_mister. The database maintainer should fix this.')

    if '..' in parts or len(parts) == 0 or parts[0] in invalid_root_folders:
        raise DbEntityValidationException(f'ERROR: Invalid file "{path}" for database: {db_id}. Path can\'t contain root folders. The database maintainer should fix this.')

    return parts

no_distribution_mister_invalid_paths: Final[tuple[str, ...]] = tuple(item.lower() for item in [FILE_MiSTer, FILE_menu_rbf])
invalid_paths: Final[tuple[str, ...]] = tuple(item.lower() for item in [FILE_MiSTer_ini, FILE_MiSTer_alt_ini, FILE_MiSTer_alt_1_ini, FILE_MiSTer_alt_2_ini, FILE_MiSTer_alt_3_ini, FILE_downloader_launcher_script, FILE_MiSTer_new])
invalid_root_folders: Final[tuple[str, ...]] = tuple(item.lower() for item in [FOLDER_linux, FOLDER_screenshots, FOLDER_savestates])
folders_with_non_overridable_files: Final[tuple[str, ...]] = tuple(item.lower() for item in [FOLDER_saves])
exceptional_paths: Final[tuple[str, ...]] = tuple(item.lower() for item in [FOLDER_linux, FOLDER_gamecontrollerdb, FILE_gamecontrollerdb, FILE_gamecontrollerdb_user, FILE_yc_txt])
distribution_mister_exceptional_paths: Final[tuple[str, ...]] = tuple(item.lower() for item in [FILE_PDFViewer, FILE_lesskey, FILE_glow])

class DbEntityValidationException(Exception): pass
