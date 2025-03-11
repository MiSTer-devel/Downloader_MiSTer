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


from enum import auto, unique, Enum
from typing import Any, Final, Optional, Tuple

from downloader.constants import SUFFIX_file_in_progress


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


class PathPackage:
    __slots__ = (
        'rel_path', 'drive', 'description',
        'ty', 'kind', 'pext_props', '_full_path'
    )

    def __init__(
        self,
        rel_path: str,
        drive: Optional[str],
        description: dict[str, Any],
        ty: PathType,
        kind: PathPackageKind,
        pext_props: Optional['PextPathProps']
    ) -> None:
        self.rel_path = rel_path
        self.drive = drive
        self.description = description
        self.ty = ty
        self.kind = kind
        self.pext_props = pext_props
        self._full_path: Optional[str] = None

    @property
    def full_path(self) -> str:
        if self._full_path is None:
            self._full_path = self.rel_path if self.drive is None else self.drive + '/' + self.rel_path
        return self._full_path

    @property
    def parent(self) -> str:
        pos = self.rel_path.rfind('/')
        if pos == -1:
            return ''
        return self.rel_path[:pos]

    def is_pext_external(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_EXTERNAL

    def is_pext_standard(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_STANDARD

    def is_pext_external_subfolder(self) -> bool:
        return self.ty == PATH_TYPE_FOLDER and self.pext_props is not None and self.pext_props.kind == PEXT_KIND_EXTERNAL and self.pext_props.is_subfolder

    def is_pext_parent(self) -> bool:
        return self.pext_props is not None and self.pext_props.kind == PEXT_KIND_PARENT

    def clone(self) -> 'PathPackage':
        return PathPackage(
            self.rel_path,
            self.drive,
            self.description,
            self.ty,
            self.kind,
            None if self.pext_props is None else self.pext_props.clone(),
        )

    def clone_as_pext(self) -> 'PathPackage':
        return PathPackage(
            self.rel_path,
            self.drive,
            self.description,
            self.ty,
            PATH_PACKAGE_KIND_PEXT,
            PextPathProps(
                PEXT_KIND_STANDARD,
                '',  # parent
                self.drive or '',
                (),  # other drives
                False  # is subfolder
            ) if self.pext_props is None else self.pext_props.clone(),
        )

    def db_path(self) -> str:
        if self.kind == PATH_PACKAGE_KIND_PEXT:
            return '|' + self.rel_path
        else:
            return self.rel_path

    def temp_path(self, already_exists: bool) -> Optional[str]:
        if 'tmp' in self.description:
            return (self.drive + '/' + self.description['tmp']) if self.drive is not None else self.description['tmp']
        else:
            return self.full_path + SUFFIX_file_in_progress if already_exists else None

    def backup_path(self) -> Optional[str]:
        if 'backup' in self.description:
            return (self.drive + '/' + self.description['backup']) if self.drive is not None else self.description['backup']
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
    ) -> None:
        self.kind = kind
        self.parent = parent
        self.drive = drive
        self.other_drives = other_drives
        self.is_subfolder = is_subfolder

    def clone(self) -> 'PextPathProps':
        return PextPathProps(
            self.kind,
            self.parent,
            self.drive,
            self.other_drives,
            self.is_subfolder,
        )

RemovedCopy = Tuple[bool, str, str]
