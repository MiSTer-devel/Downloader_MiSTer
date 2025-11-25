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


import configparser
import re
from pathlib import Path
from typing import Optional, TypeVar, Union, SupportsInt


from downloader.config import Environment, Config, default_config, InvalidConfigParameter, AllowReboot, \
    ConfigDatabaseSection, ConfigMisterSection, AllowDelete, FileChecking
from downloader.constants import FILE_downloader_ini, DEFAULT_UPDATE_LINUX_ENV, K_DEFAULT_DB_ID, K_BASE_PATH, \
    K_DB_URL, K_DOWNLOADER_THREADS_LIMIT, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, K_FILTER, K_BASE_SYSTEM_PATH, \
    K_STORAGE_PRIORITY, K_ALLOW_DELETE, K_ALLOW_REBOOT, K_VERBOSE, K_UPDATE_LINUX, K_MINIMUM_SYSTEM_FREE_SPACE_MB, \
    K_MINIMUM_EXTERNAL_FREE_SPACE_MB, STORAGE_PRIORITY_OFF, STORAGE_PRIORITY_PREFER_SD, \
    STORAGE_PRIORITY_PREFER_EXTERNAL, EXIT_ERROR_WRONG_SETUP, K_BENCH, K_HTTP_PROXY, FILE_CHECKING_FASTEST, \
    FILE_CHECKING_BALANCED, FILE_CHECKING_EXHAUSTIVE, FILE_CHECKING_VERIFY_INTEGRITY
from downloader.db_options import DbOptions, DbOptionsProps, DbOptionsValidationException
from downloader.http_gateway import http_config
from downloader.logger import Logger, time_str


class ConfigReader:
    def __init__(self, logger: Logger, env: Environment, start_time: float) -> None:
        self._logger = logger
        self._env = env
        self._start_time = start_time

    def calculate_config_path(self, current_working_dir: str) -> str:
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

    def read_config(self, config_path: str) -> Config:
        result = default_config()
        result['debug'] = self._env['DEBUG'] == 'true'
        if result['debug']:
            result['verbose'] = True
        if self._env['LOGLEVEL'] != '':
            if 'info' in self._env['LOGLEVEL']:
                result['verbose'] = False
            if 'debug' in self._env['LOGLEVEL']:
                result['verbose'] = True
            if 'bench' in self._env['LOGLEVEL']:
                result['bench'] = True
            if 'http' in self._env['LOGLEVEL']:
                result['http_logging'] = True

        self._logger.debug('Reading file:', config_path)
        self._logger.bench('ConfigReader Read config start.')

        if self._env['DEFAULT_BASE_PATH'] is not None:
            result['base_path'] = self._env['DEFAULT_BASE_PATH']
            result['base_system_path'] = self._env['DEFAULT_BASE_PATH']

        ini_config = self._load_ini_config(config_path)

        self._logger.bench('ConfigReader Load ini done.')

        default_db = self._default_db_config()

        for section in ini_config.sections():
            parser = IniParser(ini_config[section])

            section_id = section.lower()
            if section_id == 'mister':
                config_mister_section = self._parse_mister_section(result, parser)
                result.update(config_mister_section)
                continue
            elif section_id in result['databases']:
                raise InvalidConfigParameter("Can't import db for section '%s' twice" % section_id)

            self._logger.debug("Reading db section:", section)
            result['databases'][section_id] = self._parse_database_section(default_db, parser, section_id)

        self._logger.debug('Read sections done.')

        if len(result['databases']) == 0:
            self._logger.debug('Reading default db')
            self._add_default_database(ini_config, result)

        if self._env['ALLOW_REBOOT'] is not None:
            result['allow_reboot'] = AllowReboot(int(self._env['ALLOW_REBOOT']))

        result['curl_ssl'] = self._valid_max_length('CURL_SSL', self._env['CURL_SSL'], 50)
        if self._env['UPDATE_LINUX'] != DEFAULT_UPDATE_LINUX_ENV:
            result['update_linux'] = self._env['UPDATE_LINUX'] == 'true'

        if self._env['FORCED_BASE_PATH'] is not None:
            result['base_path'] = self._env['FORCED_BASE_PATH']
            result['base_system_path'] = self._env['FORCED_BASE_PATH']

        result['fail_on_file_error'] = self._env['FAIL_ON_FILE_ERROR'] == 'true'
        result['commit'] = self._valid_max_length('COMMIT', self._env['COMMIT'], 50)
        result['default_db_id'] = self._valid_db_id(K_DEFAULT_DB_ID, self._env['DEFAULT_DB_ID'])
        result['start_time'] = self._start_time
        result['logfile'] = self._env['LOGFILE']
        result['config_path'] = Path(config_path)

        if self._env['PC_LAUNCHER'] is not None:
            result['is_pc_launcher'] = True
            default_values = default_config()
            launcher_path = Path(self._env['PC_LAUNCHER'])
            if result['base_path'] != default_values['base_path']:
                self._abort_pc_launcher_wrong_paths('base', 'base_path', 'MiSTer')

            result['base_path'] = str(launcher_path.parent)

            if result['base_system_path'] != default_values['base_system_path']:
                self._abort_pc_launcher_wrong_paths('base', 'base_system_path', 'MiSTer')

            result['base_system_path'] = str(launcher_path.parent)

            if result['storage_priority'] != default_values['storage_priority'] and result['storage_priority'] != 'off':
                self._abort_pc_launcher_wrong_paths('external', 'storage_priority', 'MiSTer')

            result['storage_priority'] = 'off'
            result['allow_reboot'] = AllowReboot.NEVER
            result['update_linux'] = False
            result['logfile'] = str(launcher_path.with_suffix('.log'))
            result['rotate_logs'] = self._env['ROTATE_LOGS'] != 'false'
            result['curl_ssl'] = ''

            if result['file_checking'] != FileChecking.EXHAUSTIVE and result['file_checking'] != FileChecking.VERIFY_INTEGRITY:
                result['file_checking'] = FileChecking.EXHAUSTIVE

        if self._env['HTTP_PROXY'] or self._env['HTTPS_PROXY']:
            result['http_config'] = http_config(http_proxy=self._env['HTTP_PROXY'], https_proxy=self._env['HTTPS_PROXY'])
        elif result['http_proxy'] != '':
            result['http_config'] = http_config(http_proxy=result['http_proxy'], https_proxy=None)

        result['environment'] = self._env

        self._logger.bench('ConfigReader Read config done.')
        return result

    @staticmethod
    def _abort_pc_launcher_wrong_paths(path_kind: str, path_variable: str, section: str) -> None:
        print('Can not run the PC Launcher with custom "%s" under the [%s] section of the downloader.ini file.' % (path_variable, section))
        print('PC Launcher and custom %s paths are not possible simultaneously.' % path_kind)
        exit(EXIT_ERROR_WRONG_SETUP)

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
        result['databases'][default_db['section']] = db_section

    def _parse_database_section(self, default_db: ConfigDatabaseSection, parser: 'IniParser', section_id: str) -> ConfigDatabaseSection:
        default_db_url = default_db['db_url'] if section_id == default_db['section'].lower() else None
        db_url = parser.get_string(K_DB_URL, default_db_url)

        if db_url is None:
            raise InvalidConfigParameter("Can't import db for section '%s' without an url field" % section_id)

        description: ConfigDatabaseSection = {
            'db_url': db_url,
            'section': section_id
        }

        options = self._parse_database_options(parser, section_id)
        if options.any():
            description['options'] = options

        return description

    def _parse_database_options(self, parser: 'IniParser', section_id: str) -> DbOptions:
        options: DbOptionsProps = dict()
        if parser.has(K_BASE_PATH):
            self._logger.print(f"WARNING! Ignored option for section [{section_id}]: Since Downloader 2.0 '{K_BASE_PATH} = {parser.get_string(K_BASE_PATH, '?')}' is no longer a valid option within this block.")
        if parser.has(K_DOWNLOADER_THREADS_LIMIT):
            self._logger.print(f"WARNING! Ignored option for section [{section_id}]: Since Downloader 2.0 '{K_DOWNLOADER_THREADS_LIMIT} = {parser.get_string(K_DOWNLOADER_THREADS_LIMIT, '?')}' is no longer a valid option within this block.")
        if parser.has(K_DOWNLOADER_TIMEOUT):
            self._logger.print(f"WARNING! Ignored option for section [{section_id}]: Since Downloader 2.0 '{K_DOWNLOADER_TIMEOUT} = {parser.get_string(K_DOWNLOADER_TIMEOUT, '?')}' is no longer a valid option within this block.")
        if parser.has(K_DOWNLOADER_RETRIES):
            self._logger.print(f"WARNING! Ignored option for section [{section_id}]: Since Downloader 2.0 '{K_DOWNLOADER_RETRIES} = {parser.get_string(K_DOWNLOADER_RETRIES, '?')}' is no longer a valid option within this block.")
        if parser.has(K_FILTER):
            options['filter'] = parser.get_string(K_FILTER, '')

        try:
            return DbOptions(options)
        except DbOptionsValidationException as e:
            raise InvalidConfigParameter("Invalid options for section '%s': %s" % (section_id, e.fields_to_string()))

    def _parse_mister_section(self, result: Config, parser: 'IniParser') -> ConfigMisterSection:
        mister: ConfigMisterSection = {
            'base_path': self._valid_base_path(parser.get_string(K_BASE_PATH, result['base_path']), K_BASE_PATH),
            'base_system_path': self._valid_base_path(parser.get_string(K_BASE_SYSTEM_PATH, result['base_system_path']), K_BASE_SYSTEM_PATH),
            'storage_priority': self._valid_storage_priority(parser.get_string(K_STORAGE_PRIORITY, result['storage_priority'])),
            'allow_delete': AllowDelete(parser.get_int(K_ALLOW_DELETE, result['allow_delete'].value)),
            'allow_reboot': AllowReboot(parser.get_int(K_ALLOW_REBOOT, result['allow_reboot'].value)),
            'file_checking': self._validate_file_checking(parser.get_string('file_checking', None) or result['file_checking']),
            'verbose': parser.get_bool(K_VERBOSE, result['verbose']),
            'bench': parser.get_bool(K_BENCH, result['bench']),
            'update_linux': parser.get_bool(K_UPDATE_LINUX, result['update_linux']),
            'downloader_threads_limit': parser.get_int(K_DOWNLOADER_THREADS_LIMIT, result['downloader_threads_limit']),
            'downloader_timeout': parser.get_int(K_DOWNLOADER_TIMEOUT, result['downloader_timeout']),
            'downloader_retries': parser.get_int(K_DOWNLOADER_RETRIES, result['downloader_retries']),
            'filter': parser.get_string(K_FILTER, result['filter']).strip().lower(),
            'minimum_system_free_space_mb': parser.get_int(K_MINIMUM_SYSTEM_FREE_SPACE_MB, result['minimum_system_free_space_mb']),
            'minimum_external_free_space_mb': parser.get_int(K_MINIMUM_EXTERNAL_FREE_SPACE_MB, result['minimum_external_free_space_mb']),
            'user_defined_options': [],
            'http_proxy': parser.get_string(K_HTTP_PROXY, '').strip()
        }

        for key in mister:
            if parser.has(key):
                mister['user_defined_options'].append(key)

        return mister

    def _default_db_config(self) -> ConfigDatabaseSection:
        return {
            'db_url': self._env['DEFAULT_DB_URL'],
            'section': self._env['DEFAULT_DB_ID'].lower()
        }

    def _valid_base_path(self, path: str, key: str) -> str:
        if self._env['DEBUG'] != 'true':
            if path == '' or path[0] == '.' or path[0] == '\\':
                raise InvalidConfigParameter(f"Invalid path '{path}', {key} paths should start with '/media/*/'")

            parts = path.lower().split('/')
            if '..' in parts or len(parts) < 3 or parts[0] != '' or parts[1] != 'media':
                raise InvalidConfigParameter(f"Invalid path '{path}', {key} paths should start with '/media/*/'")

        if len(path) > 1 and path[-1] == '/':
            path = path[0:-1]

        return path

    def _valid_max_length(self, key: str, value: str, max_limit: int) -> str:
        if len(value) <= max_limit:
            return value

        raise InvalidConfigParameter(f"Invalid {key} with value '{value}'. Too long string (max is {max_limit}).")

    def _valid_db_id(self, key: str, value: str) -> str:
        value = self._valid_max_length(key, value, 255)

        regex = re.compile("^[a-zA-Z][-._a-zA-Z0-9]*[/]?[-._a-zA-Z0-9]+$")
        if regex.match(value):
            return value.lower()

        raise InvalidConfigParameter(f"Invalid {key} with value '{value}'. Not matching ID regex.")

    def _valid_storage_priority(self, parameter: str) -> str:
        lower_parameter = parameter.lower()
        if lower_parameter in [STORAGE_PRIORITY_OFF, 'false', 'no', 'base_path', '0', 'f', 'n']:
            return STORAGE_PRIORITY_OFF
        elif lower_parameter in [STORAGE_PRIORITY_PREFER_SD, STORAGE_PRIORITY_PREFER_EXTERNAL]:
            return lower_parameter
        else:
            return self._valid_base_path(parameter, K_STORAGE_PRIORITY)

    def _validate_file_checking(self, parameter: Union[str, FileChecking]) -> FileChecking:
        if isinstance(parameter, FileChecking):
            return parameter

        lower_parameter = parameter.lower()
        if lower_parameter == FILE_CHECKING_FASTEST: return FileChecking.FASTEST
        elif lower_parameter == FILE_CHECKING_BALANCED: return FileChecking.BALANCED
        elif lower_parameter == FILE_CHECKING_EXHAUSTIVE: return FileChecking.EXHAUSTIVE
        elif lower_parameter == FILE_CHECKING_VERIFY_INTEGRITY: return FileChecking.VERIFY_INTEGRITY
        else:
            self._logger.print(f'WARNING: file_checking value "{parameter}" is not recognized. Defaulting to "balanced".\n      See the documentation for valid options.')
            return FileChecking.BALANCED

TOptStr = TypeVar('TOptStr', str, Optional[str])
TOptInt = TypeVar('TOptInt', int, Optional[int])

class IniParser:
    def __init__(self, ini_args: configparser.SectionProxy) -> None:
        self._ini_args = ini_args

    def get_string(self, key: str, default: TOptStr) -> Union[str, TOptStr]:
        result = self._ini_args.get(key, default)
        if isinstance(result, str): return result.strip('"\' ')
        return result

    def get_bool(self, key: str, default: bool) -> bool:
        return strtobool(self.get_string(key, 'true' if default else 'false'))

    def get_int(self, key: str, default: TOptInt) -> Union[int, TOptInt]:
        result = self.get_string(key, None)
        if result is None: return default
        return to_int(result, default)

    def has(self, key: str) -> bool:
        return self._ini_args.get(key) is not None


TInt = TypeVar('TInt', bound=SupportsInt)

def to_int(n: Union[str, TInt], default: TOptInt) -> Union[int, TOptInt]:
    try:
        return int(n)
    except ValueError as _:
        if isinstance(default, Exception):
            raise default
        return default


def strtobool(val: str) -> bool:
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"Invalid truth value: {val}")
