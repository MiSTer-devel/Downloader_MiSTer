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

from enum import IntEnum, unique
from pathlib import Path
from typing import TypedDict, Optional, List, Dict

from downloader.constants import FILE_downloader_ini, K_BASE_PATH, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, \
    MEDIA_FAT, DISTRIBUTION_MISTER_DB_ID, K_DOWNLOADER_THREADS_LIMIT, STORAGE_PRIORITY_PREFER_SD, \
    DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB, DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB
from downloader.db_options import DbOptions


class Environment(TypedDict):
    DOWNLOADER_LAUNCHER_PATH: Optional[str]
    DOWNLOADER_INI_PATH: Optional[str]
    LOGFILE: Optional[str]
    LOGLEVEL: str
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


class ConfigDatabaseSectionRequired(TypedDict):
    section: str
    db_url: str


class ConfigDatabaseSection(ConfigDatabaseSectionRequired, total=False):
    options: DbOptions


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


class ConfigRequired(ConfigMisterSection):
    zip_file_count_threshold: int
    zip_accumulated_mb_threshold: int
    debug: bool
    default_db_id: str
    start_time: float
    logfile: Optional[str]
    is_pc_launcher: bool
    databases: Dict[str, ConfigDatabaseSection]
    config_path: Path
    commit: str
    fail_on_file_error: bool
    curl_ssl: str
    http_logging: bool

class Config(ConfigRequired, total=False):
    environment: Environment  # This should never be used. It's there just to be debug-logged.


def config_with_base_path(config: Config, base_path: str) -> Config:
    result = config.copy()
    result['base_path'] = base_path
    return result


def default_config() -> Config:
    return {
        'curl_ssl': '',
        'http_logging': False,
        'databases': {},
        'config_path': Path(FILE_downloader_ini),
        'base_path': MEDIA_FAT,
        'base_system_path': MEDIA_FAT,
        'storage_priority': STORAGE_PRIORITY_PREFER_SD,
        'allow_delete': AllowDelete.ALL,
        'allow_reboot': AllowReboot.ALWAYS,
        'update_linux': True,
        'downloader_threads_limit': 20,
        'downloader_timeout': 300,
        'downloader_retries': 3,
        'zip_file_count_threshold': 60,
        'zip_accumulated_mb_threshold': 100,
        'filter': '',
        'verbose': False,
        'debug': False,
        'default_db_id': DISTRIBUTION_MISTER_DB_ID,
        'start_time': 0,
        'logfile': None,
        'is_pc_launcher': False,
        'user_defined_options': [],
        'commit': 'unknown',
        'fail_on_file_error': False,
        'minimum_system_free_space_mb': DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB,
        'minimum_external_free_space_mb': DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB
    }


def download_sensitive_configs() -> List[str]:
    return [K_BASE_PATH, K_DOWNLOADER_THREADS_LIMIT, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES]


class InvalidConfigParameter(Exception):
    pass

