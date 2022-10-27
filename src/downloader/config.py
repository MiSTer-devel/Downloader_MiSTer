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
from pathlib import Path, PurePosixPath

from downloader.constants import FILE_downloader_ini, K_BASE_PATH, K_BASE_SYSTEM_PATH, K_STORAGE_PRIORITY, K_DATABASES, \
    K_ALLOW_DELETE, K_ALLOW_REBOOT, K_UPDATE_LINUX, K_DOWNLOADER_SIZE_MB_LIMIT, \
    K_DOWNLOADER_PROCESS_LIMIT, \
    K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD, K_FILTER, \
    K_VERBOSE, \
    K_DB_URL, K_SECTION, K_CONFIG_PATH, K_USER_DEFINED_OPTIONS, KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, \
    KENV_DEFAULT_BASE_PATH, KENV_ALLOW_REBOOT, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEBUG, K_OPTIONS, \
    MEDIA_FAT, K_DEBUG, K_CURL_SSL, KENV_CURL_SSL, KENV_UPDATE_LINUX, KENV_FAIL_ON_FILE_ERROR, KENV_COMMIT, \
    K_FAIL_ON_FILE_ERROR, K_COMMIT, K_UPDATE_LINUX_ENVIRONMENT, K_DEFAULT_DB_ID, DISTRIBUTION_MISTER_DB_ID, \
    K_START_TIME, KENV_LOGFILE, K_LOGFILE, K_DOWNLOADER_OLD_IMPLEMENTATION, K_DOWNLOADER_THREADS_LIMIT, \
    KENV_PC_LAUNCHER, K_IS_PC_LAUNCHER
from downloader.db_options import DbOptionsKind, DbOptions, DbOptionsValidationException
from downloader.ini_parser import IniParser


def config_with_base_path(config, base_path):
    result = config.copy()
    result[K_BASE_PATH] = base_path
    return result


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


@unique
class UpdateLinuxEnvironment(IntEnum):
    TRUE = 0
    FALSE = 1
    ONLY = 2


def default_config():
    return {
        K_DATABASES: {},
        K_CONFIG_PATH: Path(FILE_downloader_ini),
        K_BASE_PATH: MEDIA_FAT,
        K_BASE_SYSTEM_PATH: MEDIA_FAT,
        K_STORAGE_PRIORITY: 'prefer_sd',
        K_ALLOW_DELETE: AllowDelete.ALL,
        K_ALLOW_REBOOT: AllowReboot.ALWAYS,
        K_UPDATE_LINUX: True,
        K_DOWNLOADER_SIZE_MB_LIMIT: 100,
        K_DOWNLOADER_PROCESS_LIMIT: 300,
        K_DOWNLOADER_THREADS_LIMIT: 20,
        K_DOWNLOADER_TIMEOUT: 300,
        K_DOWNLOADER_RETRIES: 3,
        K_DOWNLOADER_OLD_IMPLEMENTATION: False,
        K_ZIP_FILE_COUNT_THRESHOLD: 60,
        K_ZIP_ACCUMULATED_MB_THRESHOLD: 100,
        K_FILTER: None,
        K_VERBOSE: False,
        K_DEBUG: False,
        K_DEFAULT_DB_ID: DISTRIBUTION_MISTER_DB_ID,
        K_START_TIME: 0,
        K_LOGFILE: None,
        K_IS_PC_LAUNCHER: False
    }


class ConfigReader:
    def __init__(self, logger, env):
        self._logger = logger
        self._env = env

    def calculate_config_path(self, current_working_dir):
        if self._env[KENV_PC_LAUNCHER] is not None:
            return str(Path(self._env[KENV_PC_LAUNCHER]).with_name('downloader.ini')).replace('\\', '/')

        ini_path = self._env.get(KENV_DOWNLOADER_INI_PATH, None)
        if ini_path is not None:
            return ini_path

        original_executable = self._env.get(KENV_DOWNLOADER_LAUNCHER_PATH, None)
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

    def read_config(self, config_path):
        self._logger.print("Reading file: %s" % config_path)

        result = default_config()
        result[K_DEBUG] = self._env[KENV_DEBUG] == 'true'
        if result[K_DEBUG]:
            result[K_VERBOSE] = True

        if self._env[KENV_DEFAULT_BASE_PATH] is not None:
            result[K_BASE_PATH] = self._env[KENV_DEFAULT_BASE_PATH]
            result[K_BASE_SYSTEM_PATH] = self._env[KENV_DEFAULT_BASE_PATH]

        ini_config = self._load_ini_config(config_path)
        default_db = self._default_db_config()

        for section in ini_config.sections():
            parser = IniParser(ini_config[section])

            section_id = section.lower()
            if section_id == 'mister':
                self._parse_mister_section(result, parser)
                continue

            self._logger.print("Reading '%s' db section" % section)
            self._parse_database_section(default_db, parser, result, section_id)

        if len(result[K_DATABASES]) == 0:
            self._logger.print('Reading default db')
            self._add_default_database(ini_config, result)

        if self._env[KENV_ALLOW_REBOOT] is not None:
            result[K_ALLOW_REBOOT] = AllowReboot(int(self._env[KENV_ALLOW_REBOOT]))

        if K_USER_DEFINED_OPTIONS not in result:
            result[K_USER_DEFINED_OPTIONS] = []

        result[K_CURL_SSL] = self._valid_max_length(KENV_CURL_SSL, self._env[KENV_CURL_SSL], 50)
        result[K_UPDATE_LINUX_ENVIRONMENT] = self._valid_update_linux_environment(KENV_UPDATE_LINUX, self._env[KENV_UPDATE_LINUX])
        result[K_FAIL_ON_FILE_ERROR] = self._env[KENV_FAIL_ON_FILE_ERROR] == 'true'
        result[K_COMMIT] = self._valid_max_length(KENV_COMMIT, self._env[KENV_COMMIT], 50)
        result[K_DEFAULT_DB_ID] = self._valid_db_id(K_DEFAULT_DB_ID, self._env[KENV_DEFAULT_DB_ID])
        result[K_START_TIME] = time.time()
        result[K_CONFIG_PATH] = config_path
        result[K_LOGFILE] = self._env[KENV_LOGFILE]

        if self._env[KENV_PC_LAUNCHER] is not None:
            result[K_IS_PC_LAUNCHER] = True
            default_values = default_config()
            launcher_path = Path(self._env[KENV_PC_LAUNCHER])
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
    def _abort_pc_launcher_wrong_paths(path_kind, path_variable, section):
        print('Can not run the PC Launcher with custom "%s" under the [%s] section of the downloader.ini file.' % (path_variable, section))
        print('PC Launcher and custom %s paths are not possible simultaneously.' % path_kind)
        exit(1)

    def _load_ini_config(self, config_path):
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        try:
            ini_config.read(config_path)
        except Exception as e:
            self._logger.debug(e)
            self._logger.print('Could not read ini file %s' % config_path)
            raise e
        return ini_config

    def _add_default_database(self, ini_config, result):
        default_db = self._default_db_config()
        result[K_DATABASES][default_db[K_SECTION]] = {
            K_DB_URL: ini_config['DEFAULT'].get(K_DB_URL, default_db[K_DB_URL]),
            K_SECTION: default_db[K_SECTION]
        }

    def _parse_database_section(self, default_db, parser, result, section_id):
        default_db_url = default_db[K_DB_URL] if section_id == default_db[K_SECTION].lower() else None
        db_url = parser.get_string(K_DB_URL, default_db_url)

        if db_url is None:
            raise InvalidConfigParameter("Can't import db for section '%s' without an url field" % section_id)
        if section_id in result[K_DATABASES]:
            raise InvalidConfigParameter("Can't import db for section '%s' twice" % section_id)

        description = {
            K_DB_URL: db_url,
            K_SECTION: section_id
        }

        options = self._parse_database_options(parser, section_id)
        if len(options.items()) > 0:
            description[K_OPTIONS] = options

        result[K_DATABASES][section_id] = description

    def _parse_database_options(self, parser, section_id):
        options = dict()
        if parser.has(K_BASE_PATH):
            options[K_BASE_PATH] = self._valid_base_path(parser.get_string(K_BASE_PATH, None), K_BASE_PATH)
        if parser.has(K_UPDATE_LINUX):
            options[K_UPDATE_LINUX] = parser.get_bool(K_UPDATE_LINUX, None)
        if parser.has(K_DOWNLOADER_SIZE_MB_LIMIT):
            options[K_DOWNLOADER_SIZE_MB_LIMIT] = parser.get_int(K_DOWNLOADER_SIZE_MB_LIMIT, None)
        if parser.has(K_DOWNLOADER_PROCESS_LIMIT):
            options[K_DOWNLOADER_PROCESS_LIMIT] = parser.get_int(K_DOWNLOADER_PROCESS_LIMIT, None)
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

    def _parse_mister_section(self, result, parser):
        mister = dict()
        mister[K_BASE_PATH] = self._valid_base_path(parser.get_string(K_BASE_PATH, result[K_BASE_PATH]), K_BASE_PATH)
        mister[K_BASE_SYSTEM_PATH] = self._valid_base_path(parser.get_string(K_BASE_SYSTEM_PATH, result[K_BASE_SYSTEM_PATH]), K_BASE_SYSTEM_PATH)
        mister[K_STORAGE_PRIORITY] = self._valid_storage_priority(parser.get_string(K_STORAGE_PRIORITY, result[K_STORAGE_PRIORITY]))
        mister[K_ALLOW_DELETE] = AllowDelete(parser.get_int(K_ALLOW_DELETE, result[K_ALLOW_DELETE].value))
        mister[K_ALLOW_REBOOT] = AllowReboot(parser.get_int(K_ALLOW_REBOOT, result[K_ALLOW_REBOOT].value))
        mister[K_VERBOSE] = parser.get_bool(K_VERBOSE, result[K_VERBOSE])
        mister[K_UPDATE_LINUX] = parser.get_bool(K_UPDATE_LINUX, result[K_UPDATE_LINUX])
        mister[K_DOWNLOADER_SIZE_MB_LIMIT] = parser.get_int(K_DOWNLOADER_SIZE_MB_LIMIT, result[K_DOWNLOADER_SIZE_MB_LIMIT])
        mister[K_DOWNLOADER_PROCESS_LIMIT] = parser.get_int(K_DOWNLOADER_PROCESS_LIMIT, result[K_DOWNLOADER_PROCESS_LIMIT])
        mister[K_DOWNLOADER_TIMEOUT] = parser.get_int(K_DOWNLOADER_TIMEOUT, result[K_DOWNLOADER_TIMEOUT])
        mister[K_DOWNLOADER_RETRIES] = parser.get_int(K_DOWNLOADER_RETRIES, result[K_DOWNLOADER_RETRIES])
        mister[K_DOWNLOADER_OLD_IMPLEMENTATION] = parser.get_bool(K_DOWNLOADER_OLD_IMPLEMENTATION, result[K_DOWNLOADER_OLD_IMPLEMENTATION])
        mister[K_FILTER] = parser.get_string(K_FILTER, result[K_FILTER])

        user_defined = []
        for key in mister:
            if parser.has(key):
                user_defined.append(key)

        mister[K_USER_DEFINED_OPTIONS] = user_defined

        result.update(mister)

    def _default_db_config(self):
        return {
            K_DB_URL: self._env[KENV_DEFAULT_DB_URL],
            K_SECTION: self._env[KENV_DEFAULT_DB_ID]
        }

    def _valid_base_path(self, path, key):
        if self._env[KENV_DEBUG] != 'true':
            if path == '' or path[0] == '.' or path[0] == '\\':
                raise InvalidConfigParameter("Invalid path '%s', %s paths should start with '/media/*/'" % (path, key))

            parts = path.lower().split('/')
            if '..' in parts or len(parts) < 3 or parts[0] != '' or parts[1] != 'media':
                raise InvalidConfigParameter("Invalid path '%s', %s paths should start with '/media/*/'" % (path, key))

        if len(path) > 1 and path[-1] == '/':
            path = path[0:-1]
        
        return path

    def _valid_max_length(self, key, value, max_limit):
        if len(value) <= max_limit:
            return value

        raise InvalidConfigParameter("Invalid %s with value '%s'. Too long string (max is %s)." % (key, value, max_limit))

    def _valid_db_id(self, key, value):
        value = self._valid_max_length(key, value, 255).lower()

        regex = re.compile("[a-z][_a-z0-9]*$")
        if regex.match(value):
            return value

        raise InvalidConfigParameter("Invalid %s with value '%s'. Not matching ID regex." % (key, value))

    def _valid_update_linux_environment(self, key, value):
        value = value.lower()
        if value == 'true':
            return UpdateLinuxEnvironment.TRUE
        elif value == 'false':
            return UpdateLinuxEnvironment.FALSE
        elif value == 'only':
            return UpdateLinuxEnvironment.ONLY

        raise InvalidConfigParameter("Wrong %s variable with value '%s'" % (key, value))

    def _valid_storage_priority(self, parameter):
        lower_parameter = parameter.lower()
        if lower_parameter in ['off', 'false', 'no', 'base_path', '0', 'f', 'n']:
            return 'off'
        elif lower_parameter in ['prefer_sd', 'prefer_external']:
            return lower_parameter
        else:
            return self._valid_base_path(parameter, K_STORAGE_PRIORITY)


class InvalidConfigParameter(Exception):
    pass


