# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

        if 'db_id' not in db_raw or not isinstance(db_raw['db_id'], str):
            raise DbEntityValidationException(
                'ERROR: db for section "%s" does not have "db_id", contact the db maintainer.' % section)
        self.db_id = db_raw['db_id'].lower()

        if self.db_id != section.lower():
            raise DbEntityValidationException(
                'ERROR: Section "%s" does not match database id "%s". Fix your INI file.' % (section,  self.db_id))

        if 'zips' not in db_raw or not isinstance(db_raw['zips'], dict):
            self._raise_not_field('zips')
        self.zips = self._create_zips(db_raw['zips'])

        if 'db_files' not in db_raw or not isinstance(db_raw['db_files'], list):
            self._raise_not_field('db_files')
        self.db_files = db_raw['db_files']

        if 'default_options' not in db_raw or not isinstance(db_raw['default_options'], dict):
            self._raise_not_field('default_options')
        self.default_options = self._create_default_options(db_raw['default_options'])

        if 'timestamp' not in db_raw or not isinstance(db_raw['timestamp'], int):
            self._raise_not_field('timestamp')
        self.timestamp = db_raw['timestamp']

        if 'files' not in db_raw or not isinstance(db_raw['files'], dict):
            self._raise_not_field('files')
        self.files = db_raw['files']

        if 'folders' not in db_raw or not isinstance(db_raw['folders'], dict):
            self._raise_not_field('folders')
        self.folders = db_raw['folders']

        if 'base_files_url' not in db_raw or not isinstance(db_raw['base_files_url'], str):
            self._raise_not_field('base_files_url')
        self.base_files_url = db_raw['base_files_url']

        self.tag_dictionary = db_raw['tag_dictionary'] if 'tag_dictionary' in db_raw and isinstance(db_raw['tag_dictionary'], dict) else {}

        self.linux = db_raw['linux'] if 'linux' in db_raw and isinstance(db_raw['linux'], dict) else None

        self.header = db_raw['header'] if 'header' in db_raw and isinstance(db_raw['header'], list) else None

    def _create_default_options(self, options):
        try:
            return DbOptions(options, kind=DbOptionsKind.DEFAULT_OPTIONS)
        except DbOptionsValidationException as e:
            raise DbEntityValidationException('ERROR: db "%s" has invalid default options [%s], contact the db maintainer.' % (self.db_id, e.fields_to_string()))

    def _create_zips(self, zips):
        return zips

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

    def _raise_not_field(self, field):
        raise DbEntityValidationException('ERROR: db "%s" does not have "%s", contact the db maintainer.' % (self.db_id, field))


class DbEntityValidationException(Exception):
    pass
