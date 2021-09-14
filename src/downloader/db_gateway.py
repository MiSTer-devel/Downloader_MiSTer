# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import tempfile
from pathlib import Path
from .other import run_successfully


class DbGateway:
    def __init__(self, config, file_service, logger):
        self._config = config
        self._file_service = file_service
        self._logger = logger

    def fetch(self, db_uri):
        if not db_uri.startswith("http"):
            if not db_uri.startswith("/"):
                db_uri = str(Path(db_uri).resolve())
            return self._file_service.load_db_from_file(db_uri)

        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                run_successfully('curl %s --silent --show-error --fail --location -o %s %s' % (
                    self._config['curl_ssl'], tmp_file.name, db_uri), self._logger)

                return self._file_service.load_db_from_file(tmp_file.name, Path(db_uri).suffix.lower())

        except Exception as e:
            self._logger.debug(e)
            self._logger.print('Could not load json from "%s"' % db_uri)
            return None