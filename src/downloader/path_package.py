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
from enum import auto, unique, Enum
from typing import Dict, Any, Optional, Tuple
import os

from downloader.constants import SUFFIX_file_in_progress


@unique
class PathType(Enum):
    FILE = auto()
    FOLDER = auto()

@unique
class PathPackageKind(Enum):
    STANDARD = auto()
    SYSTEM = auto()
    PEXT = auto()

@unique
class PextKind(Enum):
    PEXT_EXTERNAL = auto()
    PEXT_STANDARD = auto()
    PEXT_PARENT = auto()

@unique
class PathExists(Enum):
    UNCHECKED = auto()
    EXISTS = auto()
    DOES_NOT_EXIST = auto()

@dataclass
class PathPackage:
    full_path: str
    rel_path: str
    drive: Optional[str]
    description: Dict[str, Any]
    pext_props: Optional['PextPathProps'] = None
    ty: PathType = PathType.FILE
    kind: PathPackageKind = PathPackageKind.STANDARD
    exists: PathExists = PathExists.UNCHECKED

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

    def pext_drive(self) -> Optional[str]:
        if self.kind == PathPackageKind.PEXT and self.pext_props is not None:
            return self.pext_props.drive
        else:
            return None

    def temp_path(self) -> str:
        if 'tmp' in self.description:
            return os.path.join(self.drive, self.description['tmp']) if self.drive is not None else self.description['tmp']
        else:
            return self.full_path if self.exists == PathExists.DOES_NOT_EXIST else self.full_path + SUFFIX_file_in_progress

    def backup_path(self) -> Optional[str]:
        if 'backup' in self.description:
            return os.path.join(self.drive, self.description['backup']) if self.drive is not None else self.description['backup']
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
