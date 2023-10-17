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
from urllib.parse import urlparse

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
            raise DbEntityValidationException(message_from_internal_exception(e, section))
        except DbOptionsValidationException as e:
            raise DbEntityValidationException(f'ERROR: db "{section}" has invalid default options [{e.fields_to_string()}], contact the db maintainer if this error persists.')

    def _initialize(self, db_raw, section):
        if db_raw is None:
            raise _EmptyDbException()

        if not isinstance(db_raw, dict):
            raise _IncorrectFormatDbException()

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


def _mandatory(raw, key, factory):
    class _MissingKeyError:
        pass

    result = _optional(raw, key, factory, _MissingKeyError())
    if isinstance(result, _MissingKeyError):
        raise _MissingKeyException(key)

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
            raise _InvalidKeyException(k)

    return func


def zip_mandatory_fields():
    return [
        'kind',
        'description',
        'contents_file',
    ]


def _zips_validator(zips):
    if not isinstance(zips, dict):
        return False

    for zip_id, zip_desc in zips.items():
        if not isinstance(zip_id, str) or len(zip_id) == 0:
            raise _InvalidZipId(str(zip_id))
        try:
            _validate_zip_description(zip_id, zip_desc)
        except _InternalDbValidationException as e:
            raise _ZipException(zip_id, e)

    return True


def _validate_zip_description(zip_id, zip_desc):
    for field in zip_mandatory_fields():
        if field not in zip_desc:
            raise _MissingKeyException(field)

    _validate_zip_contents_file(zip_desc['contents_file'])

    if 'internal_summary' not in zip_desc and 'summary_file' not in zip_desc:
        raise _MissingSummaryException()

    if 'internal_summary' in zip_desc and 'summary_file' in zip_desc:
        raise _AmbiguousSummaryException()

    if 'internal_summary' in zip_desc:
        _validate_zip_internal_summary(zip_id, zip_desc['internal_summary'])
    elif 'summary_file' in zip_desc:
        _validate_zip_summary_file(zip_desc['summary_file'])

    kind = zip_desc['kind']
    if kind not in {'extract_all_contents', 'extract_single_files'}:
        raise _WrongKindException(kind)

    if kind == 'extract_all_contents':
        _validate_zip_kind_extract_all_contents(zip_desc)
    elif kind == 'extract_single_files':
        _validate_zip_kind_extract_single_files(zip_desc)


def _validate_zip_internal_summary(zip_id, summary):
    _mandatory(summary, 'files', _guard(_make_files_validator(None, zip_id, mandatory_zip_path=True)))
    _mandatory(summary, 'folders', _guard(_make_folders_validator(None, zip_id)))


def _validate_zip_contents_file(description):
    _mandatory(description, 'hash', _guard(lambda v: isinstance(v, str)))
    _mandatory(description, 'size', _guard(lambda v: isinstance(v, int)))
    _mandatory(description, 'url', _guard(_is_url))


def _validate_zip_summary_file(description):
    _validate_zip_contents_file(description)  # Requires same fields as contents file for now, but is still semantically different


def _validate_zip_kind_extract_all_contents(zip_desc):
    if 'target_folder_path' not in zip_desc:
        raise _MissingKeyException('target_folder_path')

    # @TODO: add more validation


def _validate_zip_kind_extract_single_files(zip_desc):
    # @TODO: add more validation
    pass


def _make_files_validator(db_id, zip_id=None, mandatory_zip_path=False):
    def validator(files):
        if not isinstance(files, dict):
            return False

        for file_path, file_description in files.items():
            try:
                _validate_single_file(db_id, file_path, file_description, zip_id, mandatory_zip_path)
            except _InternalDbValidationException as e:
                raise _InvalidFileException(file_path, e)

        return True

    return validator


def _validate_single_file(db_id, file_path, file_description, zip_id=None, mandatory_zip_path=False):
    parts = _validate_and_extract_parts_from_path(db_id, file_path)
    if parts[0] in folders_with_non_overridable_files() and file_description.get('overwrite', True):
        raise _InvalidSaveFileException(file_path)

    _mandatory(file_description, 'hash', _guard(lambda v: isinstance(v, str)))
    _mandatory(file_description, 'size', _guard(lambda v: isinstance(v, int)))
    if zip_id is not None:
        _mandatory(file_description, 'zip_id', _guard(lambda v: v == zip_id))
    if mandatory_zip_path:
        _mandatory(file_description, 'zip_path', _guard(_validate_zip_path))
    _optional(file_description, 'url', _guard(_is_url), None)
    _optional(file_description, 'tags', _guard(_is_tags), None)
    _optional(file_description, 'overwrite', _guard(_is_boolean), None)
    _optional(file_description, 'reboot', _guard(_is_boolean), None)


def _is_url(url):
    if not isinstance(url, str):
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def _is_boolean(v):
    return isinstance(v, bool)


def _is_tags(tags):
    if not isinstance(tags, list):
        return False

    for tag in tags:
        if not isinstance(tag, str) and not isinstance(tag, int):
            return False

    return True


def _make_folders_validator(db_id, zip_id=None):
    def validator(folders):
        if not isinstance(folders, dict):
            return False

        for folder_path, folder_description in folders.items():
            try:
                _validate_single_folder(db_id, folder_path, folder_description, zip_id)
            except _InternalDbValidationException as e:
                raise _InvalidFolderException(folder_path, e)

        return True

    return validator


def _validate_single_folder(db_id, folder_path, folder_description, zip_id=None):
    _validate_and_extract_parts_from_path(db_id, folder_path)
    _optional(folder_description, 'tags', _guard(_is_tags), None)
    if zip_id is not None:
        _mandatory(folder_description, 'zip_id', _guard(lambda v: v == zip_id))


def _validate_and_extract_parts_from_path(db_id, path):
    if not isinstance(path, str):
        raise _InvalidPathFormatException(path)

    if path == '' or path[0] == '/' or path[0] == '.' or path[0] == '\\':
        raise _IllegalPathException(path)

    lower_path = path.lower()
    parts = lower_path.split('/')

    if lower_path in exceptional_paths():
        return parts

    if db_id == DISTRIBUTION_MISTER_DB_ID and lower_path in distribution_mister_exceptional_paths():
        return parts

    if lower_path in invalid_paths():
        raise _IllegalPathException(path)

    if db_id != DISTRIBUTION_MISTER_DB_ID and lower_path in no_distribution_mister_invalid_paths():
        raise _IllegalPathException(path)

    if '..' in parts or len(parts) == 0 or parts[0] in invalid_root_folders():
        raise _IllegalPathException(path)

    return parts


def _validate_zip_path(zip_path):
    if not isinstance(zip_path, str):
        raise _InvalidPathFormatException(zip_path)

    if zip_path == '' or zip_path[0] == '/' or zip_path[0] == '.' or zip_path[0] == '\\':
        raise _IllegalPathException(zip_path)

    return True


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


class DbEntityValidationException(Exception): pass
class _InternalDbValidationException(Exception): pass
class _EmptyDbException(_InternalDbValidationException): pass
class _IncorrectFormatDbException(_InternalDbValidationException): pass
class _MissingSummaryException(_InternalDbValidationException): pass
class _AmbiguousSummaryException(_InternalDbValidationException): pass
class _InvalidSaveFileException(_InternalDbValidationException): pass
class _InvalidPathFormatException(_InternalDbValidationException): pass
class _IllegalPathException(_InternalDbValidationException): pass


class _MissingKeyException(_InternalDbValidationException):
    def __init__(self, key):
        self.key = key


class _InvalidKeyException(_InternalDbValidationException):
    def __init__(self, key):
        self.key = key


class _ZipException(_InternalDbValidationException):
    def __init__(self, zip_id: str, exception: _InternalDbValidationException):
        self.zip_id = zip_id
        self.exception = exception


class _InvalidZipId(_InternalDbValidationException):
    def __init__(self, bad_zip_id: str):
        self.bad_zip_id = bad_zip_id


class _InvalidFileException(_InternalDbValidationException):
    def __init__(self, file_path, exception):
        self.file_path = file_path
        self.exception = exception


class _InvalidFolderException(_InternalDbValidationException):
    def __init__(self, folder_path, exception):
        self.folder_path = folder_path
        self.exception = exception


class _WrongKindException(_InternalDbValidationException):
    def __init__(self, kind):
        self.kind = kind


def message_from_internal_exception(e: _InternalDbValidationException, section: str) -> str:
    if isinstance(e, _ZipException):
        message = message_from_zip_exception(e.exception, e.zip_id, section)
    elif isinstance(e, _InvalidZipId):
        message = f'db "{section}" has invalid zip id "{e.bad_zip_id}" in its zips section'
    elif isinstance(e, _EmptyDbException):
        message = f'db "{section}" is empty'
    elif isinstance(e, _IncorrectFormatDbException):
        message = f'db "{section}" has an incorrect format'
    elif isinstance(e, _MissingKeyException):
        message = f'db "{section}" does not have "{e.key}"'
    elif isinstance(e, _InvalidKeyException):
        message = f'db "{section}" has invalid "{e.key}"'
    elif isinstance(e, _InvalidFileException):
        message = f'db "{section}" contains invalid file "{e.file_path}" {file_folder_reason_from_exception(e.exception)}'
    elif isinstance(e, _InvalidFolderException):
        message = f'db "{section}" contains invalid folder "{e.folder_path}" {file_folder_reason_from_exception(e.exception)}'
    else:
        message = f'db "{section}" has an unknown error ({type(e).__name__})'

    return f'ERROR: {message}, contact the db maintainer if this error persists.'


def message_from_zip_exception(e: _InternalDbValidationException, zip_id: str, section: str) -> str:
    if isinstance(e, _MissingKeyException):
        return f'db "{section}" on zip "{zip_id}" does not have "{e.key}"'
    if isinstance(e, _MissingSummaryException):
        return f'db "{section}" on zip "{zip_id}" does not have summary field'
    if isinstance(e, _AmbiguousSummaryException):
        return f'db "{section}" on zip "{zip_id}" has an ambiguous summary, because both internal and external summaries are present'
    if isinstance(e, _WrongKindException):
        return f'db "{section}" on zip "{zip_id}" has wrong kind "{e.kind}"'
    elif isinstance(e, _InvalidKeyException):
        return f'db "{section}" on zip "{zip_id}" has invalid "{e.key}"'
    elif isinstance(e, _InvalidFileException):
        return f'db "{section}" on zip "{zip_id}" contains invalid file "{e.file_path}" {file_folder_reason_from_exception(e.exception)}'
    elif isinstance(e, _InvalidFolderException):
        return f'db "{section}" on zip "{zip_id}" contains invalid folder "{e.folder_path}" {file_folder_reason_from_exception(e.exception)}'
    else:
        return f'db "{section}" on zip "{zip_id}" has an unknown error ({type(e).__name__})'


def file_folder_reason_from_exception(e: _InternalDbValidationException) -> str:
    if isinstance(e, _MissingKeyException):
        return f'with no key "{e.key}"'
    elif isinstance(e, _InvalidKeyException):
        return f'with invalid key "{e.key}"'
    elif isinstance(e, _InvalidSaveFileException):
        return f'with forbidden overwrite support'
    elif isinstance(e, _InvalidPathFormatException):
        return f'with a path that is not a proper string'
    elif isinstance(e, _IllegalPathException):
        return f'with an illegal path'
    else:
        return ''
