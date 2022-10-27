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

from enum import unique, Enum

from downloader.constants import K_BASE_PATH, K_UPDATE_LINUX, K_DOWNLOADER_SIZE_MB_LIMIT, \
    K_DOWNLOADER_PROCESS_LIMIT, K_DOWNLOADER_TIMEOUT, K_DOWNLOADER_RETRIES, K_FILTER
from downloader.other import test_only


@unique
class DbOptionsKind(Enum):
    DEFAULT_OPTIONS = 1
    INI_SECTION = 2


class DbOptions:
    def __init__(self, props, kind: DbOptionsKind):
        present = set()

        if kind == DbOptionsKind.INI_SECTION:
            if K_BASE_PATH in props:
                if not isinstance(props[K_BASE_PATH], str):
                    raise DbOptionsValidationException([K_BASE_PATH])
                if len(props[K_BASE_PATH]) <= 1:
                    raise DbOptionsValidationException([K_BASE_PATH])
                if props[K_BASE_PATH][-1] == '/':
                    raise DbOptionsValidationException([K_BASE_PATH])

                present.add(K_BASE_PATH)
        elif kind == DbOptionsKind.DEFAULT_OPTIONS:
            pass
        else:
            raise ValueError("Invalid props kind: " + str(kind))

        if K_UPDATE_LINUX in props:
            if not isinstance(props[K_UPDATE_LINUX], bool):
                raise DbOptionsValidationException([K_UPDATE_LINUX])
            present.add(K_UPDATE_LINUX)
        if K_DOWNLOADER_SIZE_MB_LIMIT in props:
            if not isinstance(props[K_DOWNLOADER_SIZE_MB_LIMIT], int) or props[K_DOWNLOADER_SIZE_MB_LIMIT] < 1:
                raise DbOptionsValidationException([K_DOWNLOADER_SIZE_MB_LIMIT])
            present.add(K_DOWNLOADER_SIZE_MB_LIMIT)
        if K_DOWNLOADER_PROCESS_LIMIT in props:
            if not isinstance(props[K_DOWNLOADER_PROCESS_LIMIT], int) or props[K_DOWNLOADER_PROCESS_LIMIT] < 1:
                raise DbOptionsValidationException([K_DOWNLOADER_PROCESS_LIMIT])
            present.add(K_DOWNLOADER_PROCESS_LIMIT)
        if K_DOWNLOADER_TIMEOUT in props:
            if not isinstance(props[K_DOWNLOADER_TIMEOUT], int) or props[K_DOWNLOADER_TIMEOUT] < 1:
                raise DbOptionsValidationException([K_DOWNLOADER_TIMEOUT])
            present.add(K_DOWNLOADER_TIMEOUT)
        if K_DOWNLOADER_RETRIES in props:
            if not isinstance(props[K_DOWNLOADER_RETRIES], int) or props[K_DOWNLOADER_RETRIES] < 1:
                raise DbOptionsValidationException([K_DOWNLOADER_RETRIES])
            present.add(K_DOWNLOADER_RETRIES)
        if K_FILTER in props:
            if not isinstance(props[K_FILTER], str):
                raise DbOptionsValidationException([K_FILTER])
            present.add(K_FILTER)

        if len(present) != len(props):
            raise DbOptionsValidationException([o for o in props if o not in present])

        self._props = props

    def items(self):
        return self._props.items()

    def unwrap_props(self):
        return self._props

    def apply_to_config(self, config):
        config.update(self._props)

    @property
    @test_only
    def testable(self):
        return self._props


class DbOptionsValidationException(Exception):
    def __init__(self, fields):
        self.fields = fields

    def fields_to_string(self):
        return ', '.join(self.fields)