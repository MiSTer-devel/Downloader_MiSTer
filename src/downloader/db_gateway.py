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

from pathlib import Path


class DbGateway:
    def __init__(self, file_system, file_downloader_factory, logger):
        self._file_system = file_system
        self._logger = logger
        self._file_downloader_factory = file_downloader_factory

    def fetch_all(self, descriptions):

        file_downloader = self._file_downloader_factory.create(parallel_update=True, silent=True, hash_check=False)

        dbs = []
        files = {}
        errors = []

        for section, description in descriptions.items():
            db_url = description['db_url']
            if not db_url.startswith("http"):
                if not db_url.startswith("/"):
                    db_url = str(Path(db_url).resolve())

                self._logger.debug('Loading db from local path: %s' % db_url)
                dbs.append((section, self._file_system.load_db_from_file(db_url)))
            else:
                temp = self._file_system.temp_file()
                files[temp] = description
                self._logger.debug('Loading db from url: %s' % db_url)
                file_downloader.queue_file({"url": db_url, "hash": "ignore", "size": 0}, temp)

        file_downloader.download_files(False)

        correct_files = {files[file]['section']: file for file in file_downloader.correctly_downloaded_files()}

        for section, description in descriptions.items():
            if section in correct_files:
                try:
                    db = self._file_system.load_db_from_file(correct_files[section], Path(description['db_url']).suffix.lower())
                    dbs.append((section, db))
                except Exception as e:
                    self._logger.debug(e)
                    self._logger.print('Could not load json from "%s"' % description['db_url'])
                    errors.append(description['db_url'])

        for file in file_downloader.errors():
            description = files[file]
            self._logger.print('Could not download file from db_url: "%s"' % description['db_url'])
            errors.append(description['db_url'])

        for file in files:
            self._file_system.unlink(file)

        return dbs, errors
