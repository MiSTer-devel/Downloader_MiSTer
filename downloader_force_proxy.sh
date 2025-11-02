#!/bin/bash
# Copyright (c) 2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

set -euo pipefail

your_http_proxy_url="http://your-proxy-server-url-goes-here.com"

rm -f /media/fat/Scripts/.config/downloader/downloader_bin /media/fat/Scripts/.config/downloader/downloader_latest.zip
export http_proxy="${http_proxy:-${your_http_proxy_url}}"
/media/fat/Scripts/downloader.sh
