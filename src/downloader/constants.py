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

# Default SSL option
from enum import unique, Enum

DEFAULT_CACERT_FILE = '/etc/ssl/certs/cacert.pem'
DEFAULT_CURL_SSL_OPTIONS = '--cacert %s' % DEFAULT_CACERT_FILE

# Pre-selected database
DISTRIBUTION_MISTER_DB_URL = 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip'
DISTRIBUTION_MISTER_DB_ID = 'distribution_mister'

# Firmware files
FILE_MiSTer = 'MiSTer'
FILE_PDFViewer = 'linux/pdfviewer'
FILE_lesskey = 'linux/lesskey'
FILE_glow = 'linux/glow'
FILE_MiSTer_new = 'MiSTer.new'
FILE_MiSTer_old = '.MiSTer.old'
FILE_menu_rbf = 'menu.rbf'

# INI files
FILE_MiSTer_ini = 'MiSTer.ini'
FILE_MiSTer_alt_ini = 'MiSTer_alt.ini'
FILE_MiSTer_alt_1_ini = 'MiSTer_alt_1.ini'
FILE_MiSTer_alt_2_ini = 'MiSTer_alt_2.ini'
FILE_MiSTer_alt_3_ini = 'MiSTer_alt_3.ini'

# System folders
FOLDER_linux = 'linux'
FOLDER_saves = 'saves'
FOLDER_savestates = 'savestates'
FOLDER_screenshots = 'screenshots'
FOLDER_gamecontrollerdb = 'linux/gamecontrollerdb'
FILE_gamecontrollerdb = 'linux/gamecontrollerdb/gamecontrollerdb.txt'
FILE_gamecontrollerdb_user = 'linux/gamecontrollerdb/gamecontrollerdb_user.txt'

# Downloader files
FILE_downloader_storage = 'Scripts/.config/downloader/downloader.json.zip'
FILE_downloader_external_storage = '.downloader_db.json'
FILE_downloader_last_successful_run = 'Scripts/.config/downloader/%s.last_successful_run'
FILE_downloader_log = 'Scripts/.config/downloader/%s.log'
FILE_downloader_ini = '/media/fat/downloader.ini'
FILE_downloader_launcher_script = 'Scripts/downloader.sh'

# Linux Update files
FILE_MiSTer_version = '/MiSTer.version'
FILE_Linux_7z = '/media/fat/linux/7za'

# Reboot files
FILE_downloader_needs_reboot_after_linux_update = '/tmp/downloader_needs_reboot_after_linux_update'
FILE_mister_downloader_needs_reboot = '/tmp/MiSTer_downloader_needs_reboot'


# Standard Drives
MEDIA_USB0 = '/media/usb0'
MEDIA_USB1 = '/media/usb1'
MEDIA_USB2 = '/media/usb2'
MEDIA_USB3 = '/media/usb3'
MEDIA_USB4 = '/media/usb4'
MEDIA_USB5 = '/media/usb5'
MEDIA_FAT_CIFS = '/media/fat/cifs'
MEDIA_FAT = '/media/fat'

# Storage Priority Resolution Sequence
STORAGE_PATHS_PRIORITY_SEQUENCE = [
    MEDIA_USB0,
    MEDIA_USB1,
    MEDIA_USB2,
    MEDIA_USB3,
    MEDIA_USB4,
    MEDIA_USB5,
    MEDIA_FAT_CIFS,
    MEDIA_FAT
]


# Dictionary Keys:

# Config
K_BASE_PATH = 'base_path'
K_BASE_SYSTEM_PATH = 'base_system_path'
K_STORAGE_PRIORITY = 'storage_priority'
K_DATABASES = 'databases'
K_ALLOW_DELETE = 'allow_delete'
K_ALLOW_REBOOT = 'allow_reboot'
K_UPDATE_LINUX = 'update_linux'
K_DOWNLOADER_SIZE_MB_LIMIT = 'downloader_size_mb_limit'
K_DOWNLOADER_PROCESS_LIMIT = 'downloader_process_limit'
K_DOWNLOADER_THREADS_LIMIT = 'downloader_threads_limit'
K_DOWNLOADER_TIMEOUT = 'downloader_timeout'
K_DOWNLOADER_RETRIES = 'downloader_retries'
K_DOWNLOADER_OLD_IMPLEMENTATION = 'downloader_old_implementation'
K_ZIP_FILE_COUNT_THRESHOLD = 'zip_file_count_threshold'
K_ZIP_ACCUMULATED_MB_THRESHOLD = 'zip_accumulated_mb_threshold'
K_FILTER = 'filter'
K_VERBOSE = 'verbose'
K_CONFIG_PATH = 'config_path'
K_LOGFILE = 'logfile'
K_USER_DEFINED_OPTIONS = 'user_defined_options'
K_CURL_SSL = 'curl_ssl'
K_DB_URL = 'db_url'
K_SECTION = 'section'
K_OPTIONS = 'options'
K_DEBUG = 'debug'
K_FAIL_ON_FILE_ERROR = 'fail_on_file_error'
K_COMMIT = 'commit'
K_UPDATE_LINUX_ENVIRONMENT = 'update_linux_environment'
K_DEFAULT_DB_ID = 'default_db_id'
K_START_TIME = 'start_time'
K_IS_PC_LAUNCHER = 'is_pc_launcher'

# Env
KENV_DOWNLOADER_LAUNCHER_PATH = 'DOWNLOADER_LAUNCHER_PATH'
KENV_DOWNLOADER_INI_PATH = 'DOWNLOADER_INI_PATH'
KENV_CURL_SSL = 'CURL_SSL'
KENV_COMMIT = 'COMMIT'
KENV_ALLOW_REBOOT = 'ALLOW_REBOOT'
KENV_UPDATE_LINUX = 'UPDATE_LINUX'
KENV_DEFAULT_DB_URL = 'DEFAULT_DB_URL'
KENV_DEFAULT_DB_ID = 'DEFAULT_DB_ID'
KENV_DEFAULT_BASE_PATH = 'DEFAULT_BASE_PATH'
KENV_PC_LAUNCHER = 'PC_LAUNCHER'
KENV_DEBUG = 'DEBUG'
KENV_FAIL_ON_FILE_ERROR = 'FAIL_ON_FILE_ERROR'
KENV_LOGFILE = 'LOGFILE'


@unique
class PathType(Enum):
    FILE = 0
    FOLDER = 1
