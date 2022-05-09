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
import subprocess
from abc import ABC


class OsUtils(ABC):
    def sync(self):
        """send sync signal to the OS"""

    def reboot(self):
        """send reboot signal to the OS"""


class LinuxOsUtils(OsUtils):
    def sync(self):
        subprocess.run(['sync'], shell=False, stderr=subprocess.STDOUT)

    def reboot(self):
        subprocess.run(['reboot', 'now'], shell=False, stderr=subprocess.STDOUT)