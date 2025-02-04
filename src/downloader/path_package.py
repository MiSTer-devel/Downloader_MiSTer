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
from enum import unique, Enum
from typing import Dict, Any, Optional, Tuple
import os


@unique
class PathType(Enum):
    FILE = 0
    FOLDER = 1

@unique
class PathPackageKind(Enum):
    STANDARD = 0
    SYSTEM = 1
    PEXT = 2

@unique
class PextKind(Enum):
    PEXT_EXTERNAL = 10
    PEXT_STANDARD = 11
    PEXT_PARENT = 12

@dataclass
class PathPackage:
    full_path: str
    rel_path: str
    description: Dict[str, Any]
    ty: PathType = PathType.FILE
    kind: PathPackageKind = PathPackageKind.STANDARD
    pext_props: Optional['PextPathProps'] = None

    def __post_init__(self):
        assert (self.kind == PathPackageKind.PEXT) == (self.pext_props is not None), "PathPackage is not consistent according to its kind"

    @property
    def is_file(self) -> bool:
        return self.ty == PathType.FILE

    @property
    def is_folder(self) -> bool:
        return self.ty == PathType.FOLDER

    @property
    def is_standard(self) -> bool:
        return self.kind == PathPackageKind.STANDARD

    @property
    def is_system(self) -> bool:
        return self.kind == PathPackageKind.SYSTEM

    @property
    def is_potentially_external(self) -> bool:
        return self.kind == PathPackageKind.PEXT

    @property
    def is_pext_external(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PextKind.PEXT_EXTERNAL

    @property
    def is_pext_standard(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PextKind.PEXT_STANDARD

    @property
    def is_pext_external_subfolder(self) -> bool:
        return self.ty == PathType.FOLDER and self.pext_props is not None and self.pext_props.kind == PextKind.PEXT_EXTERNAL and self.pext_props.is_subfolder

    @property
    def is_pext_parent(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PextKind.PEXT_PARENT

    def db_path(self) -> str:
        if self.kind == PathPackageKind.PEXT:
            return '|' + self.rel_path
        else:
            return self.rel_path

    def drive(self) -> Optional[str]:
        if self.kind == PathPackageKind.PEXT and self.pext_props is not None:
            return self.pext_props.drive
        else:
            return None


@dataclass
class PextPathProps:
    kind: PextKind
    parent: str
    drive: str
    other_drives: Tuple[str, ...]
    is_subfolder: bool = False

    def parent_full_path(self):
        return os.path.join(self.drive, self.parent)


RemovedCopy = Tuple[bool, str, str, PathType]
