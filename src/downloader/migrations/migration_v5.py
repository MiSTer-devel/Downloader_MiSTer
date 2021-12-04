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

from downloader.store_migrator import MigrationBase


class MigrationV5(MigrationBase):
    def __init__(self, file_system):
        self._file_system = file_system

    version = 5

    def migrate(self, local_store):
        """remove old mister from old location in case it exists"""

        file_MiSTer_old = 'Scripts/.config/downloader/MiSTer.old'

        if self._file_system.is_file(file_MiSTer_old):
            self._file_system.unlink(file_MiSTer_old)
