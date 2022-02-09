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
default_cacert_file = '/etc/ssl/certs/cacert.pem'
default_curl_ssl_options = '--cacert %s' % default_cacert_file

# Pre-selected database
distribution_mister_db_url = 'https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip'
distribution_mister_db_id = 'distribution_mister'

# Firmware files
file_MiSTer = 'MiSTer'
file_PDFViewer = 'linux/pdfviewer'
file_lesskey = 'linux/lesskey'
file_glow = 'linux/glow'
file_MiSTer_new = 'MiSTer.new'
file_MiSTer_old = '.MiSTer.old'

# Downloader files
file_downloader_storage = 'Scripts/.config/downloader/downloader.json.zip'
file_downloader_last_successful_run = 'Scripts/.config/downloader/%s.last_successful_run'
file_downloader_log = 'Scripts/.config/downloader/%s.log'
file_downloader_ini = '/media/fat/downloader.ini'

# Linux Update files
file_MiSTer_version = '/MiSTer.version'
file_Linux_7z = '/media/fat/linux/7za'

# Reboot files
file_downloader_needs_reboot_after_linux_update = '/tmp/downloader_needs_reboot_after_linux_update'
file_mister_downloader_needs_reboot = '/tmp/MiSTer_downloader_needs_reboot'

# Games Directory Priority
gamesdir_priority = [
    '/media/usb0',
    '/media/usb1',
    '/media/usb2',
    '/media/usb3',
    '/media/usb4',
    '/media/usb5',
    '/media/fat/cifs',
]
