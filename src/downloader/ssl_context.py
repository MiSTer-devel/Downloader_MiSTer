# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import ssl
from typing import Optional


def context_from_curl_ssl(curl_ssl) -> tuple[ssl.SSLContext, Optional[Exception]]:
    try:
        context = ssl.create_default_context()

        if curl_ssl.startswith('--cacert '):
            cacert_file = curl_ssl[len('--cacert '):]
            context.load_verify_locations(cacert_file)
        elif curl_ssl == '--insecure':
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        return context, None
    except Exception as e:
        return ssl.create_default_context(), e
