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

import configparser
import json
import re
import time
from enum import IntEnum, unique
from pathlib import Path
from typing import TypedDict, Optional, List, Any, Dict, NotRequired

from downloader.constants import FILE_downloader_ini, K_BASE_PATH, K_BASE_SYSTEM_PATH, K_STORAGE_PRIORITY, K_DATABASES, \
    K_ALLOW_DELETE, K_ALLOW_REBOOT, K_UPDATE_LINUX, K_VERBOSE, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, \
    K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD, K_FILTER, K_DB_URL, K_CONFIG_PATH, \
    K_USER_DEFINED_OPTIONS, K_OPTIONS, MEDIA_FAT, K_DEBUG, K_CURL_SSL, K_FAIL_ON_FILE_ERROR, K_COMMIT, \
    K_DEFAULT_DB_ID, DISTRIBUTION_MISTER_DB_ID, K_START_TIME, K_LOGFILE, K_DOWNLOADER_THREADS_LIMIT, \
    K_IS_PC_LAUNCHER, DEFAULT_UPDATE_LINUX_ENV, STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL, \
    STORAGE_PRIORITY_OFF, K_MINIMUM_SYSTEM_FREE_SPACE_MB, K_MINIMUM_EXTERNAL_FREE_SPACE_MB, DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB, \
    DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB
from downloader.db_options import DbOptionsKind, DbOptions, DbOptionsValidationException
from downloader.ini_parser import IniParser
from downloader.logger import Logger


class Environment(TypedDict):
    DOWNLOADER_LAUNCHER_PATH: Optional[str]
    DOWNLOADER_INI_PATH: Optional[str]
    LOGFILE: Optional[str]
    CURL_SSL: str
    COMMIT: str
    ALLOW_REBOOT: Optional[str]
    UPDATE_LINUX: str
    DEFAULT_DB_URL: str
    DEFAULT_DB_ID: str
    DEFAULT_BASE_PATH: Optional[str]
    FORCED_BASE_PATH: Optional[str]
    PC_LAUNCHER: Optional[str]
    DEBUG: str
    FAIL_ON_FILE_ERROR: str


Config = Dict[str, Any]


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


class ConfigMisterSection(TypedDict):
    base_path: str
    base_system_path: str
    storage_priority: str
    allow_delete: AllowDelete
    allow_reboot: AllowReboot
    verbose: bool
    update_linux: bool
    downloader_threads_limit: int
    downloader_timeout: int
    downloader_retries: int
    filter: str
    minimum_system_free_space_mb: int
    minimum_external_free_space_mb: int
    user_defined_options: List[str]


class ConfigDatabaseSection(TypedDict):
    section: str
    db_url: str
    options: NotRequired[DbOptions]


def config_with_base_path(config: Config, base_path: str) -> Config:
    result = config.copy()
    result[K_BASE_PATH] = base_path
    return result


def default_config() -> Config:
    return {
        K_DATABASES: {},
        K_CONFIG_PATH: Path(FILE_downloader_ini),
        K_BASE_PATH: MEDIA_FAT,
        K_BASE_SYSTEM_PATH: MEDIA_FAT,
        K_STORAGE_PRIORITY: STORAGE_PRIORITY_PREFER_SD,
        K_ALLOW_DELETE: AllowDelete.ALL,
        K_ALLOW_REBOOT: AllowReboot.ALWAYS,
        K_UPDATE_LINUX: True,
        K_DOWNLOADER_THREADS_LIMIT: 20,
        K_DOWNLOADER_TIMEOUT: 300,
        K_DOWNLOADER_RETRIES: 3,
        K_ZIP_FILE_COUNT_THRESHOLD: 60,
        K_ZIP_ACCUMULATED_MB_THRESHOLD: 100,
        K_FILTER: None,
        K_VERBOSE: False,
        K_DEBUG: False,
        K_DEFAULT_DB_ID: DISTRIBUTION_MISTER_DB_ID,
        K_START_TIME: 0,
        K_LOGFILE: None,
        K_IS_PC_LAUNCHER: False,
        K_USER_DEFINED_OPTIONS: [],
        K_COMMIT: 'unknown',
        K_FAIL_ON_FILE_ERROR: False,
        K_MINIMUM_SYSTEM_FREE_SPACE_MB: DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB,
        K_MINIMUM_EXTERNAL_FREE_SPACE_MB: DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB
    }


def download_sensitive_configs() -> List[str]:
    return [K_BASE_PATH, K_DOWNLOADER_THREADS_LIMIT, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES]


class ConfigReader:
    def __init__(self, logger: Logger, env: Environment):
        self._logger = logger
        self._env = env

    def calculate_config_path(self, current_working_dir) -> str:
        if self._env['PC_LAUNCHER'] is not None:
            return str(Path(self._env['PC_LAUNCHER']).with_name('downloader.ini')).replace('\\', '/')

        ini_path = self._env.get('DOWNLOADER_INI_PATH', None)
        if ini_path is not None:
            return ini_path

        original_executable = self._env.get('DOWNLOADER_LAUNCHER_PATH', None)
        if original_executable is None:
            return FILE_downloader_ini

        executable_path = Path(original_executable)

        if str(executable_path.parent) == '.':
            executable_path = Path(current_working_dir) / executable_path
            original_executable = str(executable_path).replace('\\', '/')

        list_of_parents = [str(p.name) for p in reversed(executable_path.parents) if
                           p.name.lower() != 'scripts' and p.name != '']

        if len(list_of_parents) == 0:
            parents = ''
        else:
            parents = '/'.join(list_of_parents) + '/'

        result = ('/' if original_executable[0] in '/' else './') + parents + executable_path.stem + '.ini'

        return result.replace('/update.ini', '/downloader.ini')

    def read_config(self, config_path) -> Config:
        self._logger.print("Reading file: %s" % config_path)

        result = default_config()
        result[K_DEBUG] = self._env['DEBUG'] == 'true'
        if result[K_DEBUG]:
            result[K_VERBOSE] = True

        if self._env['DEFAULT_BASE_PATH'] is not None:
            result[K_BASE_PATH] = self._env['DEFAULT_BASE_PATH']
            result[K_BASE_SYSTEM_PATH] = self._env['DEFAULT_BASE_PATH']

        ini_config = self._load_ini_config(config_path)
        default_db = self._default_db_config()

        for section in ini_config.sections():
            parser = IniParser(ini_config[section])

            section_id = section.lower()
            if section_id == 'mister':
                self._parse_mister_section(result, parser)
                continue
            elif section_id in result[K_DATABASES]:
                raise InvalidConfigParameter("Can't import db for section '%s' twice" % section_id)

            self._logger.print("Reading '%s' db section" % section)
            result[K_DATABASES][section_id] = self._parse_database_section(default_db, parser, section_id)

        if len(result[K_DATABASES]) == 0:
            self._logger.print('Reading default db')
            self._add_default_database(ini_config, result)

        if self._env['ALLOW_REBOOT'] is not None:
            result[K_ALLOW_REBOOT] = AllowReboot(int(self._env['ALLOW_REBOOT']))

        if K_USER_DEFINED_OPTIONS not in result:
            result[K_USER_DEFINED_OPTIONS] = []

        result[K_CURL_SSL] = self._valid_max_length('CURL_SSL', self._env['CURL_SSL'], 50)
        if self._env['UPDATE_LINUX'] != DEFAULT_UPDATE_LINUX_ENV:
            result[K_UPDATE_LINUX] = self._env['UPDATE_LINUX'] == 'true'

        if self._env['FORCED_BASE_PATH'] is not None:
            result[K_BASE_PATH] = self._env['FORCED_BASE_PATH']
            result[K_BASE_SYSTEM_PATH] = self._env['FORCED_BASE_PATH']
            for section, db in result[K_DATABASES].items():
                if K_OPTIONS in db: db[K_OPTIONS].remove_base_path()

        result[K_FAIL_ON_FILE_ERROR] = self._env['FAIL_ON_FILE_ERROR'] == 'true'
        result[K_COMMIT] = self._valid_max_length('COMMIT', self._env['COMMIT'], 50)
        result[K_DEFAULT_DB_ID] = self._valid_db_id(K_DEFAULT_DB_ID, self._env['DEFAULT_DB_ID'])
        result[K_START_TIME] = time.time()
        result[K_CONFIG_PATH] = config_path
        result[K_LOGFILE] = self._env['LOGFILE']

        if self._env['PC_LAUNCHER'] is not None:
            result[K_IS_PC_LAUNCHER] = True
            default_values = default_config()
            launcher_path = Path(self._env['PC_LAUNCHER'])
            if result[K_BASE_PATH] != default_values[K_BASE_PATH]:
                self._abort_pc_launcher_wrong_paths('base', 'base_path', 'MiSTer')

            result[K_BASE_PATH] = str(launcher_path.parent)

            if result[K_BASE_SYSTEM_PATH] != default_values[K_BASE_SYSTEM_PATH]:
                self._abort_pc_launcher_wrong_paths('base', 'base_system_path', 'MiSTer')

            result[K_BASE_SYSTEM_PATH] = str(launcher_path.parent)
            for section, db in result[K_DATABASES].items():
                if K_OPTIONS in db and K_BASE_PATH in db[K_OPTIONS].unwrap_props():
                    section_props = db[K_OPTIONS].unwrap_props()
                    if section_props[K_BASE_PATH] != default_values[K_BASE_PATH]:
                        self._abort_pc_launcher_wrong_paths('base', 'base_path', section)

                    section_props[K_BASE_PATH] = str(launcher_path.parent)

            if result[K_STORAGE_PRIORITY] != default_values[K_STORAGE_PRIORITY] and result[K_STORAGE_PRIORITY] != 'off':
                self._abort_pc_launcher_wrong_paths('external', 'storage_priority', 'MiSTer')

            result[K_STORAGE_PRIORITY] = 'off'
            result[K_ALLOW_REBOOT] = AllowReboot.NEVER
            result[K_UPDATE_LINUX] = False
            result[K_LOGFILE] = str(launcher_path.with_suffix('.log'))
            result[K_CURL_SSL] = ''

        self._logger.configure(result)

        self._logger.debug('env: ' + json.dumps(self._env, indent=4))
        self._logger.debug('config: ' + json.dumps(result, default=lambda o: o.__dict__, indent=4))

        result[K_CONFIG_PATH] = Path(result[K_CONFIG_PATH])

        return result

    @staticmethod
    def _abort_pc_launcher_wrong_paths(path_kind: str, path_variable: str, section: str) -> None:
        print('Can not run the PC Launcher with custom "%s" under the [%s] section of the downloader.ini file.' % (path_variable, section))
        print('PC Launcher and custom %s paths are not possible simultaneously.' % path_kind)
        exit(1)

    def _load_ini_config(self, config_path) -> configparser.ConfigParser:
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        try:
            ini_config.read(config_path)
        except Exception as e:
            self._logger.debug(e)
            self._logger.print('Could not read ini file %s' % config_path)
            raise e
        return ini_config

    def _add_default_database(self, ini_config: configparser.ConfigParser, result: Config) -> None:
        default_db = self._default_db_config()
        db_section: ConfigDatabaseSection = {
            'db_url': ini_config['DEFAULT'].get(K_DB_URL, default_db['db_url']),
            'section': default_db['section']
        }
        result[K_DATABASES][default_db['section']] = db_section

    def _parse_database_section(self, default_db: ConfigDatabaseSection, parser: IniParser, section_id: str) -> ConfigDatabaseSection:
        default_db_url = default_db['db_url'] if section_id == default_db['section'].lower() else None
        db_url = parser.get_string(K_DB_URL, default_db_url)

        if db_url is None:
            raise InvalidConfigParameter("Can't import db for section '%s' without an url field" % section_id)

        description: ConfigDatabaseSection = {
            'db_url': db_url,
            'section': section_id
        }

        options = self._parse_database_options(parser, section_id)
        if len(options.items()) > 0:
            description['options'] = options

        return description

    def _parse_database_options(self, parser: IniParser, section_id: str) -> DbOptions:
        options = dict()
        if parser.has(K_BASE_PATH):
            options[K_BASE_PATH] = self._valid_base_path(parser.get_string(K_BASE_PATH, None), K_BASE_PATH)
        if parser.has(K_DOWNLOADER_THREADS_LIMIT):
            options[K_DOWNLOADER_THREADS_LIMIT] = parser.get_int(K_DOWNLOADER_THREADS_LIMIT, None)
        if parser.has(K_DOWNLOADER_TIMEOUT):
            options[K_DOWNLOADER_TIMEOUT] = parser.get_int(K_DOWNLOADER_TIMEOUT, None)
        if parser.has(K_DOWNLOADER_RETRIES):
            options[K_DOWNLOADER_RETRIES] = parser.get_int(K_DOWNLOADER_RETRIES, None)
        if parser.has(K_FILTER):
            options[K_FILTER] = parser.get_string(K_FILTER, None)

        try:
            return DbOptions(options, kind=DbOptionsKind.INI_SECTION)
        except DbOptionsValidationException as e:
            raise InvalidConfigParameter("Invalid options for section '%s': %s" % (section_id, e.fields_to_string()))

    def _parse_mister_section(self, result: Config, parser: IniParser) -> None:
        mister: ConfigMisterSection = {
            'base_path': self._valid_base_path(parser.get_string(K_BASE_PATH, result[K_BASE_PATH]), K_BASE_PATH),
            'base_system_path': self._valid_base_path(parser.get_string(K_BASE_SYSTEM_PATH, result[K_BASE_SYSTEM_PATH]), K_BASE_SYSTEM_PATH),
            'storage_priority': self._valid_storage_priority(parser.get_string(K_STORAGE_PRIORITY, result[K_STORAGE_PRIORITY])),
            'allow_delete': AllowDelete(parser.get_int(K_ALLOW_DELETE, result[K_ALLOW_DELETE].value)),
            'allow_reboot': AllowReboot(parser.get_int(K_ALLOW_REBOOT, result[K_ALLOW_REBOOT].value)),
            'verbose': parser.get_bool(K_VERBOSE, result[K_VERBOSE]),
            'update_linux': parser.get_bool(K_UPDATE_LINUX, result[K_UPDATE_LINUX]),
            'downloader_threads_limit': parser.get_int(K_DOWNLOADER_THREADS_LIMIT, result[K_DOWNLOADER_THREADS_LIMIT]),
            'downloader_timeout': parser.get_int(K_DOWNLOADER_TIMEOUT, result[K_DOWNLOADER_TIMEOUT]),
            'downloader_retries': parser.get_int(K_DOWNLOADER_RETRIES, result[K_DOWNLOADER_RETRIES]),
            'filter': parser.get_string(K_FILTER, result[K_FILTER]),
            'minimum_system_free_space_mb': parser.get_int(K_MINIMUM_SYSTEM_FREE_SPACE_MB, result[K_MINIMUM_SYSTEM_FREE_SPACE_MB]),
            'minimum_external_free_space_mb': parser.get_int(K_MINIMUM_EXTERNAL_FREE_SPACE_MB, result[K_MINIMUM_EXTERNAL_FREE_SPACE_MB]),
            'user_defined_options': []
        }

        for key in mister:
            if parser.has(key):
                mister['user_defined_options'].append(key)

        result.update(mister)

    def _default_db_config(self) -> ConfigDatabaseSection:
        return {
            'db_url': self._env['DEFAULT_DB_URL'],
            'section': self._env['DEFAULT_DB_ID'].lower()
        }

    def _valid_base_path(self, path: str, key: str) -> str:
        if self._env['DEBUG'] != 'true':
            if path == '' or path[0] == '.' or path[0] == '\\':
                raise InvalidConfigParameter("Invalid path '%s', %s paths should start with '/media/*/'" % (path, key))

            parts = path.lower().split('/')
            if '..' in parts or len(parts) < 3 or parts[0] != '' or parts[1] != 'media':
                raise InvalidConfigParameter("Invalid path '%s', %s paths should start with '/media/*/'" % (path, key))

        if len(path) > 1 and path[-1] == '/':
            path = path[0:-1]
        
        return path

    def _valid_max_length(self, key: str, value: str, max_limit: int) -> str:
        if len(value) <= max_limit:
            return value

        raise InvalidConfigParameter("Invalid %s with value '%s'. Too long string (max is %s)." % (key, value, max_limit))

    def _valid_db_id(self, key: str, value: str) -> str:
        value = self._valid_max_length(key, value, 255)

        regex = re.compile("^[a-zA-Z][-._a-zA-Z0-9]*[/]?[-._a-zA-Z0-9]+$")
        if regex.match(value):
            return value.lower()

        raise InvalidConfigParameter("Invalid %s with value '%s'. Not matching ID regex." % (key, value))

    def _valid_storage_priority(self, parameter: str) -> str:
        lower_parameter = parameter.lower()
        if lower_parameter in [STORAGE_PRIORITY_OFF, 'false', 'no', 'base_path', '0', 'f', 'n']:
            return STORAGE_PRIORITY_OFF
        elif lower_parameter in [STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL]:
            return lower_parameter
        else:
            return self._valid_base_path(parameter, K_STORAGE_PRIORITY)


class InvalidConfigParameter(Exception):
    pass


