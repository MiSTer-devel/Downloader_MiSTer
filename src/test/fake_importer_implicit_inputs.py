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
from downloader.config import default_config


class ImporterImplicitInputs:
    def __init__(self, files=None, folders=None, system_paths=None, base_path=None, config=None, problematic_files=None, actual_description=None, missing_files=None):
        config = default_config() if config is None else config

        self.files = files
        self.folders = folders
        self.system_paths = system_paths
        self.base_path = base_path
        self.config = config
        self.problematic_files = problematic_files
        self.actual_description = actual_description
        self.missing_files = missing_files
