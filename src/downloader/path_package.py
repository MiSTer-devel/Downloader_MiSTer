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


from enum import auto, unique, Enum
from typing import Dict, Any, Final, Optional, Tuple
import os

from downloader.constants import SUFFIX_file_in_progress


is_windows: Final = os.name == 'nt'

@unique
class PathType(Enum):
    FILE = auto()
    FOLDER = auto()

PATH_TYPE_FILE: Final = PathType.FILE
PATH_TYPE_FOLDER: Final = PathType.FOLDER


@unique
class PathPackageKind(Enum):
    STANDARD = auto()
    SYSTEM = auto()
    PEXT = auto()

PATH_PACKAGE_KIND_STANDARD: Final = PathPackageKind.STANDARD
PATH_PACKAGE_KIND_SYSTEM: Final = PathPackageKind.SYSTEM
PATH_PACKAGE_KIND_PEXT: Final = PathPackageKind.PEXT


@unique
class PextKind(Enum):
    PEXT_EXTERNAL = auto()
    PEXT_STANDARD = auto()
    PEXT_PARENT = auto()

PEXT_KIND_EXTERNAL: Final = PextKind.PEXT_EXTERNAL
PEXT_KIND_STANDARD: Final = PextKind.PEXT_STANDARD
PEXT_KIND_PARENT: Final = PextKind.PEXT_PARENT


@unique
class PathExists(Enum):
    UNCHECKED = auto()
    EXISTS = auto()
    DOES_NOT_EXIST = auto()

PATH_EXISTS_UNCHECKED: Final = PathExists.UNCHECKED
PATH_EXISTS_EXISTS: Final = PathExists.EXISTS
PATH_EXISTS_DOES_NOT_EXIST: Final = PathExists.DOES_NOT_EXIST


class PathPackage:
    __slots__ = (
        'rel_path', 'drive', 'description',
        'ty', 'kind', 'pext_props', 'full_path', 'exists'
    )

    def __init__(
        self,
        rel_path: str,
        drive: Optional[str],
        description:Dict[str, Any],
        ty: PathType,
        kind: PathPackageKind,
        pext_props: Optional['PextPathProps'], /
    ):
        self.rel_path = rel_path
        self.drive = drive
        self.description = description
        self.ty = ty
        self.kind = kind
        self.pext_props = pext_props
        self.full_path = rel_path if drive is None else os.path.join(drive, rel_path) if is_windows else drive + '/' + rel_path
        self.exists = PATH_EXISTS_UNCHECKED

    def is_pext_external(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_EXTERNAL

    def is_pext_standard(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_STANDARD

    def is_pext_external_subfolder(self) -> bool:
        return self.ty == PATH_TYPE_FOLDER and self.pext_props is not None and self.pext_props.kind == PEXT_KIND_EXTERNAL and self.pext_props.is_subfolder

    def is_pext_parent(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_PARENT

    def db_path(self) -> str:
        if self.kind == PATH_PACKAGE_KIND_PEXT:
            return '|' + self.rel_path
        else:
            return self.rel_path

    def pext_drive(self) -> Optional[str]:
        if self.kind == PATH_PACKAGE_KIND_PEXT and self.pext_props is not None:
            return self.pext_props.drive
        else:
            return None

    def temp_path(self) -> str:
        if 'tmp' in self.description:
            return (os.path.join(self.drive, self.description['tmp']) if is_windows else self.drive + '/' + self.description['tmp']) if self.drive is not None else self.description['tmp']
        else:
            return self.full_path if self.exists == PATH_EXISTS_DOES_NOT_EXIST else self.full_path + SUFFIX_file_in_progress

    def backup_path(self) -> Optional[str]:
        if 'backup' in self.description:
            return (os.path.join(self.drive, self.description['backup']) if is_windows else self.drive + '/' + self.description['backup']) if self.drive is not None else self.description['backup']
        else:
            return None

class PextPathProps:
    __slots__ = ('kind', 'parent', 'drive', 'other_drives', 'is_subfolder')

    def __init__(
        self,
        kind: PextKind,
        parent: str,
        drive: str,
        other_drives: Tuple[str, ...],
        is_subfolder: bool,/
    ):
        self.kind = kind
        self.parent = parent
        self.drive = drive
        self.other_drives = other_drives
        self.is_subfolder = is_subfolder

    def parent_pkg(self) -> PathPackage:
        return PathPackage(self.parent, self.drive, {}, PATH_TYPE_FOLDER, PATH_PACKAGE_KIND_PEXT, PextPathProps(
            PEXT_KIND_PARENT, self.parent, self.drive, self.other_drives, False
        ))


RemovedCopy = Tuple[bool, str, str, PathType]
