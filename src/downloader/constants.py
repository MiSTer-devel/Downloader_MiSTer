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

from typing import Final, Tuple, List

# Default SSL option

DEFAULT_CACERT_FILE: Final[str] = '/etc/ssl/certs/cacert.pem'
DEFAULT_CURL_SSL_OPTIONS: Final[str] = '--cacert %s' % DEFAULT_CACERT_FILE
DEFAULT_UPDATE_LINUX_ENV: Final[str] = 'undefined'
DEFAULT_MINIMUM_SYSTEM_FREE_SPACE_MB: Final[int] = 512
DEFAULT_MINIMUM_EXTERNAL_FREE_SPACE_MB: Final[int] = 128

# Pre-selected database
DISTRIBUTION_MISTER_DB_URL: Final[str] = 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip'
DISTRIBUTION_MISTER_DB_ID: Final[str] = 'distribution_mister'

# File System affixes
SUFFIX_file_in_progress: Final[str] = '._downloader_in_progress'

# Firmware files
FILE_MiSTer: Final[str] = 'MiSTer'
FILE_PDFViewer: Final[str] = 'linux/pdfviewer'
FILE_lesskey: Final[str] = 'linux/lesskey'
FILE_glow: Final[str] = 'linux/glow'
FILE_MiSTer_new: Final[str] = 'MiSTer.new'
FILE_MiSTer_old: Final[str] = '.MiSTer.old'
FILE_menu_rbf: Final[str] = 'menu.rbf'

# INI files
FILE_MiSTer_ini: Final[str] = 'MiSTer.ini'
FILE_MiSTer_alt_ini: Final[str] = 'MiSTer_alt.ini'
FILE_MiSTer_alt_1_ini: Final[str] = 'MiSTer_alt_1.ini'
FILE_MiSTer_alt_2_ini: Final[str] = 'MiSTer_alt_2.ini'
FILE_MiSTer_alt_3_ini: Final[str] = 'MiSTer_alt_3.ini'

# System folders
FOLDER_linux: Final[str] = 'linux'
FOLDER_saves: Final[str] = 'saves'
FOLDER_savestates: Final[str] = 'savestates'
FOLDER_screenshots: Final[str] = 'screenshots'
FOLDER_gamecontrollerdb: Final[str] = 'linux/gamecontrollerdb'
FILE_gamecontrollerdb: Final[str] = 'linux/gamecontrollerdb/gamecontrollerdb.txt'
FILE_gamecontrollerdb_user: Final[str] = 'linux/gamecontrollerdb/gamecontrollerdb_user.txt'
FILE_yc_txt: Final[str] = 'yc.txt'

# Downloader files
FILE_downloader_storage_zip: Final[str] = 'Scripts/.config/downloader/downloader.json.zip'
FILE_downloader_storage_json: Final[str] = 'Scripts/.config/downloader/downloader.json'
FILE_downloader_external_storage: Final[str] = '.downloader_db.json'
FILE_downloader_last_successful_run: Final[str] = 'Scripts/.config/downloader/%s.last_successful_run'
FILE_downloader_log: Final[str] = 'Scripts/.config/downloader/%s.log'
FILE_downloader_ini: Final[str] = '/media/fat/downloader.ini'
FILE_downloader_launcher_script: Final[str] = 'Scripts/downloader.sh'

# Linux Update files
FILE_MiSTer_version: Final[str] = '/MiSTer.version'
FILE_Linux_uninstalled: Final[str] = '/media/fat/linux.7z'
FILE_7z_util: Final[str] = '/media/fat/linux/7za'
FILE_7z_util_uninstalled: Final[str] = '/media/fat/linux/7za.gz'
def FILE_7z_util_uninstalled_description(): return {
    'url': 'https://github.com/MiSTer-devel/SD-Installer-Win64_MiSTer/raw/master/7za.gz',
    'hash': 'ed1ad5185fbede55cd7fd506b3c6c699',
    'size': 465600
}
FILE_Linux_user_files: Final[List[Tuple[str, str]]] = [
    # source -> destination
    ('/media/fat/linux/hostname', '/etc/hostname'),
    ('/media/fat/linux/hosts', '/etc/hosts'),
    ('/media/fat/linux/interfaces', '/etc/network/interfaces'),
    ('/media/fat/linux/resolv.conf', '/etc/resolv.conf'),
    ('/media/fat/linux/dhcpcd.conf', '/etc/dhcpcd.conf'),
    ('/media/fat/linux/fstab', '/etc/fstab'),
]

# Reboot files
FILE_downloader_needs_reboot_after_linux_update: Final[str] = '/tmp/downloader_needs_reboot_after_linux_update'
FILE_mister_downloader_needs_reboot: Final[str] = '/tmp/MiSTer_downloader_needs_reboot'

# Hash exceptional cases
HASH_file_does_not_exist: Final[str] = 'file_does_not_exist'

# Storage Priority
STORAGE_PRIORITY_PREFER_SD: Final[str] = 'prefer_sd'
STORAGE_PRIORITY_PREFER_EXTERNAL: Final[str] = 'prefer_external'
STORAGE_PRIORITY_OFF: Final[str] = 'off'

# Standard Drives
MEDIA_USB0: Final[str] = '/media/usb0'
MEDIA_USB1: Final[str] = '/media/usb1'
MEDIA_USB2: Final[str] = '/media/usb2'
MEDIA_USB3: Final[str] = '/media/usb3'
MEDIA_USB4: Final[str] = '/media/usb4'
MEDIA_USB5: Final[str] = '/media/usb5'
MEDIA_FAT_CIFS: Final[str] = '/media/fat/cifs'
MEDIA_FAT: Final[str] = '/media/fat'

# Storage Priority Resolution Sequence
STORAGE_PATHS_PRIORITY_SEQUENCE: Final[List[str]] = [
    MEDIA_USB0,
    MEDIA_USB1,
    MEDIA_USB2,
    MEDIA_USB3,
    MEDIA_USB4,
    MEDIA_USB5,
    MEDIA_FAT_CIFS,
    MEDIA_FAT
]

# Filters

ESSENTIAL_TERM: Final[str] = 'essential'

# Dictionary Keys:

# Config
K_BASE_PATH: Final[str] = 'base_path'
K_BASE_SYSTEM_PATH: Final[str] = 'base_system_path'
K_STORAGE_PRIORITY: Final[str] = 'storage_priority'
K_DATABASES: Final[str] = 'databases'
K_ALLOW_DELETE: Final[str] = 'allow_delete'
K_ALLOW_REBOOT: Final[str] = 'allow_reboot'
K_UPDATE_LINUX: Final[str] = 'update_linux'
K_DOWNLOADER_THREADS_LIMIT: Final[str] = 'downloader_threads_limit'
K_DOWNLOADER_TIMEOUT: Final[str] = 'downloader_timeout'
K_DOWNLOADER_RETRIES: Final[str] = 'downloader_retries'
K_ZIP_FILE_COUNT_THRESHOLD: Final[str] = 'zip_file_count_threshold'
K_ZIP_ACCUMULATED_MB_THRESHOLD: Final[str] = 'zip_accumulated_mb_threshold'
K_FILTER: Final[str] = 'filter'
K_VERBOSE: Final[str] = 'verbose'
K_CONFIG_PATH: Final[str] = 'config_path'
K_USER_DEFINED_OPTIONS: Final[str] = 'user_defined_options'
K_CURL_SSL: Final[str] = 'curl_ssl'
K_DB_URL: Final[str] = 'db_url'
K_SECTION: Final[str] = 'section'
K_OPTIONS: Final[str] = 'options'
K_DEBUG: Final[str] = 'debug'
K_FAIL_ON_FILE_ERROR: Final[str] = 'fail_on_file_error'
K_COMMIT: Final[str] = 'commit'
K_DEFAULT_DB_ID: Final[str] = 'default_db_id'
K_START_TIME: Final[str] = 'start_time'
K_IS_PC_LAUNCHER: Final[str] = 'is_pc_launcher'
K_MINIMUM_SYSTEM_FREE_SPACE_MB: Final[str] = 'minimum_system_free_space_mb'
K_MINIMUM_EXTERNAL_FREE_SPACE_MB: Final[str] = 'minimum_external_free_space_mb'

# Env
KENV_DOWNLOADER_LAUNCHER_PATH: Final[str] = 'DOWNLOADER_LAUNCHER_PATH'
KENV_DOWNLOADER_INI_PATH: Final[str] = 'DOWNLOADER_INI_PATH'
KENV_CURL_SSL: Final[str] = 'CURL_SSL'
KENV_COMMIT: Final[str] = 'COMMIT'
KENV_ALLOW_REBOOT: Final[str] = 'ALLOW_REBOOT'
KENV_UPDATE_LINUX: Final[str] = 'UPDATE_LINUX'
KENV_DEFAULT_DB_URL: Final[str] = 'DEFAULT_DB_URL'
KENV_DEFAULT_DB_ID: Final[str] = 'DEFAULT_DB_ID'
KENV_DEFAULT_BASE_PATH: Final[str] = 'DEFAULT_BASE_PATH'
KENV_FORCED_BASE_PATH: Final[str] = 'FORCED_BASE_PATH'
KENV_PC_LAUNCHER: Final[str] = 'PC_LAUNCHER'
KENV_DEBUG: Final[str] = 'DEBUG'
KENV_FAIL_ON_FILE_ERROR: Final[str] = 'FAIL_ON_FILE_ERROR'
KENV_LOGFILE: Final[str] = 'LOGFILE'
KENV_LOGLEVEL: Final[str] = 'LOGLEVEL'

# Db State Signature
DB_STATE_SIGNATURE_NO_HASH: Final[str] = 'non_initialized_hash'
DB_STATE_SIGNATURE_NO_SIZE: Final[int] = -123
DB_STATE_SIGNATURE_NO_TIMESTAMP: Final[int] = 0
DB_STATE_SIGNATURE_NO_FILTER: Final[str] = ''

# Exit error codes
EXIT_ERROR_WRONG_SETUP = 10
EXIT_ERROR_NO_CERTS = 11
EXIT_ERROR_BAD_NEW_BINARY = 12
EXIT_ERROR_STORE_NOT_SAVED = 13
EXIT_ERROR_FAILED_FILES = 20
EXIT_ERROR_FAILED_DBS = 21
