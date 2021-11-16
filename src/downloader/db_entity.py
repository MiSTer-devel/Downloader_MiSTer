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
import json


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
            raise DbEntityValidationException('ERROR: db "%s" does not have "zips", contact the db maintainer.' % self.db_id)
        self.zips = db_raw['zips']

        if 'db_files' not in db_raw or not isinstance(db_raw['db_files'], list):
            raise DbEntityValidationException('ERROR: db "%s" does not have "db_files", contact the db maintainer.' % self.db_id)
        self.db_files = db_raw['db_files']

        if 'default_options' not in db_raw or not isinstance(db_raw['default_options'], dict):
            raise DbEntityValidationException(
                'ERROR: db "%s" does not have "default_options", contact the db maintainer.' % self.db_id)
        self.default_options = db_raw['default_options']

        if 'timestamp' not in db_raw or not isinstance(db_raw['timestamp'], int):
            raise DbEntityValidationException('ERROR: db "%s" does not have "timestamp", contact the db maintainer.' % self.db_id)
        self.timestamp = db_raw['timestamp']

        if 'files' not in db_raw or not isinstance(db_raw['files'], dict):
            raise DbEntityValidationException('ERROR: db "%s" does not have "files", contact the db maintainer.' % self.db_id)
        self.files = db_raw['files']

        if 'folders' not in db_raw or not isinstance(db_raw['folders'], dict):
            raise DbEntityValidationException('ERROR: db "%s" does not have "folders", contact the db maintainer.' % self.db_id)
        self.folders = db_raw['folders']

        if 'base_files_url' not in db_raw or not isinstance(db_raw['base_files_url'], str):
            raise DbEntityValidationException(
                'ERROR: db "%s" does not have "base_files_url", contact the db maintainer.' % self.db_id)
        self.base_files_url = db_raw['base_files_url']

        self.linux = db_raw['linux'] if 'linux' in db_raw and isinstance(db_raw['linux'], dict) else None

        self.header = db_raw['header'] if 'header' in db_raw and isinstance(db_raw['header'], list) else None

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def to_dict(self):
        result = json.loads(self.to_json())
        if result['linux'] is None:
            result.pop('linux')
        if result['header'] is None:
            result.pop('header')
        return result


class DbEntityValidationException(Exception):
    pass
