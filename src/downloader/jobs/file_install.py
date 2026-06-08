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

from typing import Optional

from downloader.file_system import FileSystem
from downloader.path_package import PathPackage

FileInstallPaths = tuple[str, Optional[str], Optional[str]]


def prepare_file_install(file_system: FileSystem, pkg: PathPackage, already_exists: bool) -> FileInstallPaths:
    temp_path = pkg.temp_path(already_exists)
    backup_path = pkg.backup_path()
    target_path = pkg.full_path

    if temp_path is None and backup_path is not None and file_system.is_file(target_path, use_cache=False):
        file_system.copy(target_path, backup_path)

    return temp_path or target_path, temp_path, backup_path


def finalize_file_install(file_system: FileSystem, install_path: str, target_path: str, backup_path: Optional[str]) -> None:
    if install_path == target_path:
        return

    if backup_path is not None and file_system.is_file(target_path, use_cache=False):  # @TODO: See if use_cache is needed
        file_system.copy(target_path, backup_path)

    file_system.move(install_path, target_path)
