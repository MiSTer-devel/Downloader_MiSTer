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
from .store_migrator import MigrationBase


class MigrationV1(MigrationBase):
    version = 1

    def migrate(self, local_store):

        #
        # create 'dbs' field
        #
        db_ids = list(local_store.keys())
        dbs = dict()
        for db_id in db_ids:
            dbs[db_id] = local_store[db_id]
            local_store.pop(db_id)

        local_store['dbs'] = dbs

        #
        # create 'zips' fields
        #
        for db_id in local_store['dbs']:
            local_store['dbs'][db_id]['zips'] = dict()
