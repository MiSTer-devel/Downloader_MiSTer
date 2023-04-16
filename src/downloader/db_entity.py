# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from typing import Dict, Any, List

from downloader.constants import FILE_MiSTer, FILE_menu_rbf, FILE_MiSTer_ini, FILE_MiSTer_alt_ini, \
    FILE_downloader_launcher_script, FILE_MiSTer_alt_3_ini, FILE_MiSTer_alt_1_ini, FILE_MiSTer_alt_2_ini, \
    FILE_MiSTer_new, FOLDER_linux, FOLDER_saves, FOLDER_savestates, FOLDER_screenshots, FILE_PDFViewer, FILE_lesskey, \
    FILE_glow, FOLDER_gamecontrollerdb, FILE_gamecontrollerdb, DISTRIBUTION_MISTER_DB_ID, FILE_gamecontrollerdb_user, FILE_yc_txt
from downloader.db_options import DbOptionsKind, DbOptions, DbOptionsValidationException
from downloader.other import test_only, cache


class DbEntity:
    def __init__(self, db_raw, section):
        try:
            self._initialize(db_raw, section)
        except _InternalDbValidationException as e:
            raise DbEntityValidationException('ERROR: %s, contact the db maintainer if this error persists.' % e.message_for_section(section))
        except DbOptionsValidationException as e:
            raise DbEntityValidationException('ERROR: db "%s" has invalid default options [%s], contact the db maintainer if this error persists.' % (section, e.fields_to_string()))

    def _initialize(self, db_raw, section):
        if db_raw is None:
            raise _InternalDbValidationException(lambda sec: 'db "%s" is empty' % sec)

        if not isinstance(db_raw, dict):
            raise _InternalDbValidationException(lambda sec: 'db "%s" has incorrect format' % sec)

        self.db_id: str = _mandatory(db_raw, 'db_id', lambda db_id, _: _create_db_id(db_id, section))
        self.timestamp: int = _mandatory(db_raw, 'timestamp', _guard(lambda v: isinstance(v, int)))
        self.files: Dict[str, Any] = _mandatory(db_raw, 'files', _guard(_make_files_validator(section)))
        self.folders: Dict[str, Any] = _mandatory(db_raw, 'folders', _guard(_make_folders_validator(section)))

        self.zips: Dict[str, Any] = _optional(db_raw, 'zips', _guard(_zips_validator), {})
        self.db_files: List[str] = _optional(db_raw, 'db_files', _guard(lambda v: isinstance(v, list)), [])
        self.default_options: DbOptions = _optional(db_raw, 'default_options', lambda v, _: DbOptions(v, kind=DbOptionsKind.DEFAULT_OPTIONS), DbOptions({}, DbOptionsKind.DEFAULT_OPTIONS))
        self.base_files_url: str = _optional(db_raw, 'base_files_url', _guard(lambda v: isinstance(v, str)), '')
        self.tag_dictionary: Dict[str, int] = _optional(db_raw, 'tag_dictionary', _guard(lambda v: isinstance(v, dict)), {})
        self.linux: Dict[str, Any] = _optional(db_raw, 'linux', _guard(lambda v: isinstance(v, dict)), None)
        self.header: List[str] = _optional(db_raw, 'header', _guard(lambda v: isinstance(v, list)), [])

    @property
    @test_only
    def testable(self):  # pragma: no cover
        result = self.__dict__.copy()
        result['default_options'] = result['default_options'].testable
        if result['linux'] is None:
            result.pop('linux')
        if result['header'] is None:
            result.pop('header')
        return result


class DbEntityValidationException(Exception):
    pass


class _InternalDbValidationException(Exception):
    def __init__(self, message_factory):
        self._message_factory = message_factory

    def message_for_section(self, section):
        return self._message_factory(section)


class _InvalidPathException(_InternalDbValidationException):
    def __init__(self, path):
        self._path = path

    def message_for_section(self, section):
        return 'db "%s" contains invalid path "%s"' % (section, self._path)


def _mandatory(raw, key, factory):
    class _MissingKeyError:
        pass

    result = _optional(raw, key, factory, _MissingKeyError())
    if isinstance(result, _MissingKeyError):
        raise _InternalDbValidationException(lambda section: 'db "%s" does not have "%s"' % (section, key))

    return result


def _optional(raw, key, factory, default):
    if key not in raw:
        return default

    return factory(raw[key], key)


def _create_db_id(db_id, section):
    valid_id = _guard(lambda v: isinstance(v, str))(db_id, 'db_id').lower()

    if valid_id != section.lower():
        raise DbEntityValidationException('ERROR: Section "%s" does not match database id "%s". Fix your INI file.' % (section, valid_id))

    return valid_id


def _guard(validator):
    def func(v, k):
        if validator(v):
            return v
        else:
            raise _InternalDbValidationException(lambda section: 'db "%s" has invalid "%s"' % (section, k))

    return func


def zip_mandatory_fields():
    return [
        'kind',
        'description',
        'contents_file',
#        'files_count',
#        'folders_count',
#        'raw_files_size'
    ]


def _zips_validator(zips):
    if not isinstance(zips, dict):
        return False

    mandatory_fields = zip_mandatory_fields()

    for zip_id, zip_desc in zips.items():
        for field in mandatory_fields:
            if field not in zip_desc:
                raise _InternalDbValidationException(lambda section: 'db "%s" has invalid ZIP "%s" with missing field "%s"' % (section, zip_id, field))

        if 'internal_summary' not in zip_desc and 'summary_file' not in zip_desc:
            raise _InternalDbValidationException(lambda section: 'db "%s" has invalid ZIP "%s" with missing summary field' % (section, zip_id))

        if zip_desc['kind'] not in {'extract_all_contents', 'extract_single_files'}:
            raise _InternalDbValidationException(lambda section: 'db "%s" has invalid ZIP "%s" with wrong kind "%s".' % (section, zip_id, zip_desc['kind']))

        if zip_desc['kind'] == 'extract_all_contents' and 'target_folder_path' not in zip_desc:
            raise _InternalDbValidationException(lambda section: 'db "%s" has invalid ZIP "%s" with missing target_folder_path field' % (section, zip_id))

    return True


def _make_files_validator(db_id):
    def validator(files):
        if not isinstance(files, dict):
            return False

        for file_path, file_description in files.items():
            parts = _validate_and_extract_parts_from_path(db_id, file_path)
            if parts[0] in folders_with_non_overridable_files() and file_description.get('overwrite', True):
                raise _InternalDbValidationException(lambda section: 'db "%s" contains save "%s" with unallowed overwrite support' % (section, file_path))

        return True

    return validator


def _make_folders_validator(db_id):
    def validator(folders):
        if not isinstance(folders, dict):
            return False

        for folder_path, folder_description in folders.items():
            _validate_and_extract_parts_from_path(db_id, folder_path)

        return True

    return validator


def _validate_and_extract_parts_from_path(db_id, path):
    if not isinstance(path, str):
        raise _InternalDbValidationException(lambda section: 'db "%s" contains path that is not a string "%s"' % (section, str(path)))

    if path == '' or path[0] == '/' or path[0] == '.' or path[0] == '\\':
        raise _InvalidPathException(path)

    lower_path = path.lower()
    parts = lower_path.split('/')

    if lower_path in exceptional_paths():
        return parts

    if db_id == DISTRIBUTION_MISTER_DB_ID and lower_path in distribution_mister_exceptional_paths():
        return parts

    if lower_path in invalid_paths():
        raise _InvalidPathException(path)

    if db_id != DISTRIBUTION_MISTER_DB_ID and lower_path in no_distribution_mister_invalid_paths():
        raise _InvalidPathException(path)

    if '..' in parts or len(parts) == 0 or parts[0] in invalid_root_folders():
        raise _InvalidPathException(path)

    return parts


@cache
def no_distribution_mister_invalid_paths():
    return tuple(item.lower() for item in [FILE_MiSTer, FILE_menu_rbf])


@cache
def invalid_paths():
    return tuple(item.lower() for item in
                 [FILE_MiSTer_ini, FILE_MiSTer_alt_ini, FILE_MiSTer_alt_1_ini, FILE_MiSTer_alt_2_ini,
                  FILE_MiSTer_alt_3_ini, FILE_downloader_launcher_script, FILE_MiSTer_new])


@cache
def invalid_root_folders():
    return tuple(item.lower() for item in [FOLDER_linux, FOLDER_screenshots, FOLDER_savestates])


@cache
def folders_with_non_overridable_files():
    return tuple(item.lower() for item in [FOLDER_saves])

@cache
def exceptional_paths():
    return tuple(item.lower() for item in [FOLDER_linux, FOLDER_gamecontrollerdb, FILE_gamecontrollerdb, FILE_gamecontrollerdb_user, FILE_yc_txt])

@cache
def distribution_mister_exceptional_paths():
    return tuple(item.lower() for item in [FILE_PDFViewer, FILE_lesskey, FILE_glow])

