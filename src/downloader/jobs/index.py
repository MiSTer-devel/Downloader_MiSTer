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

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Index:
    files: Dict[str, Any]
    folders: Dict[str, Any]
    base_files_url: Optional[str] = None

    def merge_zip_index(self, zip_index: 'Index'):
        self.files.update(zip_index.files)
        self.folders.update(zip_index.folders)

    def subtract(self, other: 'Index'):
        for key in other.files:
            if key in self.files:
                del self.files[key]

        for key in other.folders:
            if key in self.folders:
                del self.folders[key]


