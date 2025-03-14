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

from downloader.config import Config
from downloader.constants import MEDIA_FAT
from downloader.store_migrator import MigrationBase


class MigrationV5(MigrationBase):
    def __init__(self, config: Config) -> None:
        self._config = config

    version = 5

    def migrate(self, local_store) -> None:
        """remove old mister from old location in case it exists"""
        try:
            from pathlib import Path
            mister_old = Path(self._config.get('base_system_path', MEDIA_FAT)) / 'Scripts/.config/downloader/MiSTer.old'
            if mister_old.is_file():
                mister_old.unlink(missing_ok=True)
        except Exception as e:
            print(e)
