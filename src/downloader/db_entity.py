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

from downloader.db_options import DbOptionsKind, DbOptions, DbOptionsValidationException
from downloader.other import test_only


class DbEntity:
    def __init__(self, db_raw, section):
        if db_raw is None:
            raise DbEntityValidationException('ERROR: empty db.')

        if not isinstance(db_raw, dict):
            raise DbEntityValidationException('ERROR: db has incorrect format, contact the db maintainer if this error persists.')

        self.db_id = _mandatory(db_raw, 'db_id', lambda db_id, _: _create_db_id(db_id, section))
        try:
            self._take_other_fields(db_raw)
        except DbEntityValidationException as e:
            raise DbEntityValidationException(str(e).replace('DB_ID', self.db_id))

    def _take_other_fields(self, db_raw):
        self.timestamp = _mandatory(db_raw, 'timestamp', _guard(lambda v: isinstance(v, int)))
        self.files = _mandatory(db_raw, 'files', _guard(lambda v: isinstance(v, dict)))
        self.folders = _mandatory(db_raw, 'folders', _guard(lambda v: isinstance(v, dict)))

        self.zips = _optional(db_raw, 'zips', _guard(_is_valid_zips), {})
        self.db_files = _optional(db_raw, 'db_files', _guard(lambda v: isinstance(v, list)), [])
        self.default_options = _optional(db_raw, 'default_options', _create_default_options, DbOptions({}, DbOptionsKind.DEFAULT_OPTIONS))
        self.base_files_url = _optional(db_raw, 'base_files_url', _guard(lambda v: isinstance(v, str)), '')
        self.tag_dictionary = _optional(db_raw, 'tag_dictionary', _guard(lambda v: isinstance(v, dict)), {})
        self.linux = _optional(db_raw, 'linux', _guard(lambda v: isinstance(v, dict)), None)
        self.header = _optional(db_raw, 'header', _guard(lambda v: isinstance(v, list)), [])

    @property
    @test_only
    def testable(self):
        result = self.__dict__.copy()
        result['default_options'] = result['default_options'].testable
        if result['linux'] is None:
            result.pop('linux')
        if result['header'] is None:
            result.pop('header')
        return result


class DbEntityValidationException(Exception):
    pass


def _mandatory(raw, key, factory):
    class _Error:
        pass

    result = _optional(raw, key, factory, _Error())
    if isinstance(result, _Error):
        raise DbEntityValidationException('ERROR: db "DB_ID" does not have "%s", contact the db maintainer.' % key)

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


def _guard(predicate):
    def func(v, k):
        if predicate(v):
            return v
        else:
            raise DbEntityValidationException('ERROR: db "DB_ID" has invalid "%s", contact the db maintainer.' % k)
    return func


def _create_default_options(options, _):
    try:
        return DbOptions(options, kind=DbOptionsKind.DEFAULT_OPTIONS)
    except DbOptionsValidationException as e:
        raise DbEntityValidationException('ERROR: db "DB_ID" has invalid default options [%s], contact the db maintainer.' % e.fields_to_string())


def _is_valid_zips(zips):
    if not isinstance(zips, dict):
        return False

    mandatory_fields = [
        'kind',
        'description',
        'contents_file',
#        'files_count',
#        'folders_count',
#        'raw_files_size'
    ]

    for zip_id, zip_desc in zips.items():
        for field in mandatory_fields:
            if field not in zip_desc:
                raise DbEntityValidationException('ERROR: db "DB_ID" has invalid ZIP "%s" with missing field "%s", contact the db maintainer.' % (zip_id, field))

        if 'internal_summary' not in zip_desc and 'summary_file' not in zip_desc:
            raise DbEntityValidationException('ERROR: db "DB_ID" has invalid ZIP "%s" with missing summary field, contact the db maintainer.' % zip_id)

        if zip_desc['kind'] == 'extract_all_contents' and 'target_folder_path' not in zip_desc:
            raise DbEntityValidationException('ERROR: db "DB_ID" has invalid ZIP "%s" with missing target_folder_path field, contact the db maintainer.' % zip_id)

    return True
