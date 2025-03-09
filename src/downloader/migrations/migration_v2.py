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

from downloader.store_migrator import MigrationBase


class MigrationV2(MigrationBase):
    version = 2

    def migrate(self, local_store):
        """convert 'folders' from list to dict"""

        for db_id in local_store['dbs']:
            local_store['dbs'][db_id]['folders'] = {folder: {} for folder in local_store['dbs'][db_id]['folders']}
            for zip_id in local_store['dbs'][db_id]['zips']:
                if 'folders' in local_store['dbs'][db_id]['zips'][zip_id]:
                    local_store['dbs'][db_id]['zips'][zip_id]['folders'] = {folder: {} for folder in local_store['dbs'][db_id]['zips'][zip_id]['folders']}
                else:
                    local_store['dbs'][db_id]['zips'][zip_id]['folders'] = {}
