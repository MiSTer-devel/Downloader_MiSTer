# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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
from typing import Optional

from downloader.constants import DOWNLOADER_VERSION, FILE_downloader_run_signal


class VersionService:
    def print_version(self, release_patch: Optional[int]) -> int:
        self._remove_run_signal()
        suffix = str(release_patch) if release_patch is not None else 'dev'
        print(f'{DOWNLOADER_VERSION}.{suffix}')
        return 0

    @staticmethod
    def _remove_run_signal() -> None:
        try:
            Path(FILE_downloader_run_signal).unlink(missing_ok=True)
        except OSError:
            pass
