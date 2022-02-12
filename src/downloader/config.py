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
from enum import IntEnum, unique
from pathlib import Path, PurePosixPath

from downloader.constants import FILE_downloader_ini, K_BASE_PATH, K_BASE_SYSTEM_PATH, K_GAMESDIR_PATH, K_DATABASES, \
    K_ALLOW_DELETE, K_ALLOW_REBOOT, K_UPDATE_LINUX, K_PARALLEL_UPDATE, K_DOWNLOADER_SIZE_MB_LIMIT, K_DOWNLOADER_PROCESS_LIMIT, \
    K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, K_ZIP_FILE_COUNT_THRESHOLD, K_ZIP_ACCUMULATED_MB_THRESHOLD, K_FILTER, K_VERBOSE, \
    K_DB_URL, K_SECTION, K_CONFIG_PATH, K_USER_DEFINED_OPTIONS, KENV_DOWNLOADER_INI_PATH, KENV_DOWNLOADER_LAUNCHER_PATH, \
    KENV_DEFAULT_BASE_PATH, KENV_ALLOW_REBOOT, KENV_DEFAULT_DB_URL, KENV_DEFAULT_DB_ID, KENV_DEBUG, K_OPTIONS, MEDIA_FAT
from downloader.db_options import DbOptionsKind, DbOptions, DbOptionsValidationException
from downloader.ini_parser import IniParser


def config_file_path(env, current_working_dir):
    ini_path = env.get(KENV_DOWNLOADER_INI_PATH, None)
    if ini_path is not None:
        return ini_path

    original_executable = env.get(KENV_DOWNLOADER_LAUNCHER_PATH, None)
    if original_executable is None:
        return FILE_downloader_ini

    executable_path = PurePosixPath(original_executable)

    if str(executable_path.parent) == '.':
        executable_path = PurePosixPath(current_working_dir) / executable_path
        original_executable = str(executable_path)

    list_of_parents = [str(p.name) for p in reversed(executable_path.parents) if p.name.lower() != 'scripts' and p.name != '']

    if len(list_of_parents) == 0:
        parents = ''
    else:
        parents = '/'.join(list_of_parents) + '/'

    return ('/' if original_executable[0] == '/' else './') + parents + executable_path.stem + '.ini'


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


def default_config():
    return {
        K_DATABASES: {},
        K_BASE_PATH: MEDIA_FAT,
        K_BASE_SYSTEM_PATH: MEDIA_FAT,
        K_GAMESDIR_PATH: 'auto',
        K_ALLOW_DELETE: AllowDelete.ALL,
        K_ALLOW_REBOOT: AllowReboot.ALWAYS,
        K_UPDATE_LINUX: True,
        K_PARALLEL_UPDATE: True,
        K_DOWNLOADER_SIZE_MB_LIMIT: 100,
        K_DOWNLOADER_PROCESS_LIMIT: 300,
        K_DOWNLOADER_TIMEOUT: 300,
        K_DOWNLOADER_RETRIES: 3,
        K_ZIP_FILE_COUNT_THRESHOLD: 60,
        K_ZIP_ACCUMULATED_MB_THRESHOLD: 100,
        K_FILTER: None,
        K_VERBOSE: False
    }


class ConfigReader:
    def __init__(self, logger, env):
        self._logger = logger
        self._env = env

    def read_config(self, config_path):
        result = default_config()
        result[K_CONFIG_PATH] = Path(config_path)
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

        return result

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
            options[K_BASE_PATH] = self._valid_base_path(parser.get_string(K_BASE_PATH, None))
        if parser.has(K_PARALLEL_UPDATE):
            options[K_PARALLEL_UPDATE] = parser.get_bool(K_PARALLEL_UPDATE, None)
        if parser.has(K_UPDATE_LINUX):
            options[K_UPDATE_LINUX] = parser.get_bool(K_UPDATE_LINUX, None)
        if parser.has(K_DOWNLOADER_SIZE_MB_LIMIT):
            options[K_DOWNLOADER_SIZE_MB_LIMIT] = parser.get_int(K_DOWNLOADER_SIZE_MB_LIMIT, None)
        if parser.has(K_DOWNLOADER_PROCESS_LIMIT):
            options[K_DOWNLOADER_PROCESS_LIMIT] = parser.get_int(K_DOWNLOADER_PROCESS_LIMIT, None)
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
        mister[K_BASE_PATH] = self._valid_base_path(parser.get_string(K_BASE_PATH, result[K_BASE_PATH]))
        mister[K_BASE_SYSTEM_PATH] = self._valid_base_path(parser.get_string(K_BASE_SYSTEM_PATH, result[K_BASE_SYSTEM_PATH]))
        mister[K_ALLOW_DELETE] = AllowDelete(parser.get_int(K_ALLOW_DELETE, result[K_ALLOW_DELETE].value))
        mister[K_ALLOW_REBOOT] = AllowReboot(parser.get_int(K_ALLOW_REBOOT, result[K_ALLOW_REBOOT].value))
        mister[K_VERBOSE] = parser.get_bool(K_VERBOSE, result[K_VERBOSE])
        mister[K_PARALLEL_UPDATE] = parser.get_bool(K_PARALLEL_UPDATE, result[K_PARALLEL_UPDATE])
        mister[K_UPDATE_LINUX] = parser.get_bool(K_UPDATE_LINUX, result[K_UPDATE_LINUX])
        mister[K_DOWNLOADER_SIZE_MB_LIMIT] = parser.get_int(K_DOWNLOADER_SIZE_MB_LIMIT, result[K_DOWNLOADER_SIZE_MB_LIMIT])
        mister[K_DOWNLOADER_PROCESS_LIMIT] = parser.get_int(K_DOWNLOADER_PROCESS_LIMIT, result[K_DOWNLOADER_PROCESS_LIMIT])
        mister[K_DOWNLOADER_TIMEOUT] = parser.get_int(K_DOWNLOADER_TIMEOUT, result[K_DOWNLOADER_TIMEOUT])
        mister[K_DOWNLOADER_RETRIES] = parser.get_int(K_DOWNLOADER_RETRIES, result[K_DOWNLOADER_RETRIES])
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

    def _valid_base_path(self, path):
        if self._env[KENV_DEBUG] != 'true':
            if path == '' or path[0] == '.' or path[0] == '\\':
                raise InvalidConfigParameter("Invalid base path '%s', base paths should start with '/media/*/'" % path)

            parts = path.lower().split('/')
            if '..' in parts or len(parts) < 3 or parts[0] != '' or parts[1] != 'media':
                raise InvalidConfigParameter("Invalid base path '%s', base paths should start with '/media/*/'" % path)

        if len(path) > 1 and path[-1] == '/':
            path = path[0:-1]
        
        return path


class InvalidConfigParameter(Exception):
    pass


