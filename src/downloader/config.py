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

import configparser
from enum import IntEnum, unique
from pathlib import Path, PurePosixPath

from .constants import file_downloader_ini
from .ini_parser import IniParser


def config_file_path(env):
    ini_path = env.get('DOWNLOADER_INI_PATH', None)
    if ini_path is not None:
        return ini_path

    original_executable = env.get('DOWNLOADER_LAUNCHER_PATH', None)
    if original_executable is None:
        return file_downloader_ini

    executable_path = PurePosixPath(original_executable)

    list_of_parents = [str(p.name) for p in reversed(executable_path.parents) if p.name.lower() != 'scripts' and p.name != '']

    if len(list_of_parents) == 0:
        parents = ''
    else:
        parents = '/'.join(list_of_parents) + '/'

    return ('/' if original_executable[0] == '/' else './') + parents + executable_path.stem + '.ini'


@unique
class AllowDelete(IntEnum):
    NONE = 0
    ALL = 1
    OLD_RBF = 2


@unique
class AllowReboot(IntEnum):
    NEVER = 0
    ALWAYS = 1
    ONLY_AFTER_LINUX_UPDATE = 2


def default_config():
    return {
        'databases': {},
        'base_path': '/media/fat/',
        'base_system_path': '/media/fat/',
        'allow_delete': AllowDelete.ALL,
        'allow_reboot': AllowReboot.ALWAYS,
        'check_manually_deleted_files': True,
        'update_linux': True,
        'parallel_update': True,
        'downloader_size_mb_limit': 100,
        'downloader_process_limit': 300,
        'downloader_timeout': 300,
        'downloader_retries': 3,
        'zip_file_count_threshold': 60,
        'verbose': False
    }


class ConfigReader:
    def __init__(self, logger, env):
        self._logger = logger
        self._env = env

    def default_db_config(self):
        return {
            'db_url': self._env['DEFAULT_DB_URL'],
            'section': self._env['DEFAULT_DB_ID']
        }

    def read_config(self, config_path):
        result = default_config()
        result['config_path'] = Path(config_path)

        default_db = self.default_db_config()

        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        try:
            ini_config.read(config_path)
        except Exception as e:
            self._logger.debug(e)
            self._logger.print('Could not read ini file %s' % config_path)
            raise e

        for section in ini_config.sections():
            parser = IniParser(ini_config[section])

            section_id = section.lower()
            if section_id == 'mister':
                result['base_path'] = self._valid_base_path(parser.get_string('base_path', result['base_path']))
                result['base_system_path'] = self._valid_base_path(parser.get_string('base_system_path', result['base_system_path']))
                result['allow_delete'] = AllowDelete(parser.get_int('allow_delete', result['allow_delete'].value))
                result['allow_reboot'] = AllowReboot(parser.get_int('allow_reboot', result['allow_reboot'].value))
                result['check_manually_deleted_files'] = parser.get_bool('check_manually_deleted_files', result['check_manually_deleted_files'])
                result['verbose'] = parser.get_bool('verbose', result['verbose'])
                result['parallel_update'] = parser.get_bool('parallel_update', result['parallel_update'])
                result['update_linux'] = parser.get_bool('update_linux', result['update_linux'])
                result['downloader_size_mb_limit'] = parser.get_int('downloader_size_mb_limit',
                                                                    result['downloader_size_mb_limit'])
                result['downloader_process_limit'] = parser.get_int('downloader_process_limit',
                                                                    result['downloader_process_limit'])
                result['downloader_timeout'] = parser.get_int('downloader_timeout', result['downloader_timeout'])
                result['downloader_retries'] = parser.get_int('downloader_retries', result['downloader_retries'])
                continue

            self._logger.print("Reading '%s' db section" % section)
            default_db_url = default_db['db_url'] if section_id == default_db['section'].lower() else None
            db_url = parser.get_string('db_url', default_db_url)
            if db_url is None:
                raise InvalidConfigParameter("Can't import db for section '%s' without an url field" % section)

            if section_id in result['databases']:
                raise InvalidConfigParameter("Can't import db for section '%s' twice" % section)

            result['databases'][section_id] = {
                'db_url': db_url,
                'section': section_id
            }

        if len(result['databases']) == 0:
            self._logger.print('Reading default db')
            result['databases'][default_db['section']] = {
                'db_url': ini_config['DEFAULT'].get('db_url', default_db['db_url']),
                'section': default_db['section']
            }

        if self._env['ALLOW_REBOOT'] is not None:
            result['allow_reboot'] = AllowReboot(int(self._env['ALLOW_REBOOT']))

        return result

    def _valid_base_path(self, path):
        if self._env['DEBUG'] != 'true':
            if path == '' or path[0] == '.' or path[0] == '\\':
                raise InvalidConfigParameter("Invalid base path '%s', base paths should start with '/media/*/'" % path)

            parts = path.lower().split('/')
            if '..' in parts or len(parts) < 3 or parts[0] != '' or parts[1] != 'media':
                raise InvalidConfigParameter("Invalid base path '%s', base paths should start with '/media/*/'" % path)
        
        return path


class InvalidConfigParameter(Exception):
    pass
