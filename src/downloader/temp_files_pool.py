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
import os


class TempFilesPool:
    def __init__(self, file_system):
        self._file_system = file_system
        self._temp_files = []

    def make_temp_file(self):
        temp_file = self._file_system.unique_temp_filename()
        self._temp_files.append(temp_file)
        return temp_file.value

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.cleanup()

    def cleanup(self):
        for temp_file in self._temp_files:
            if os.path.exists(temp_file.value):
                os.unlink(temp_file.value)
            temp_file.close()
        self._temp_files = []
