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

from downloader.store_migrator import MigrationBase


class MigrationV3(MigrationBase):
    version = 3

    def migrate(self, local_store):
        """move 'folders' from zips to upper level"""

        for db in local_store['dbs'].values():
            for zip_id, zip_description in db['zips'].items():
                if 'folders' not in zip_description:
                    continue
                for folder_path, folder_description in zip_description['folders'].items():
                    db['folders'][folder_path] = folder_description
                    db['folders'][folder_path]['zip_id'] = zip_id
                zip_description.pop('folders')
