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

from typing import Set, TypedDict, Any, Optional


class DbOptionsProps(TypedDict, total=False):
    filter: str


class DbOptions:
    def __init__(self, props: Any) -> None:
        if not isinstance(props, dict):
            raise DbOptionsValidationException('Database-scoped options has improper format.')

        present: Set[str] = set()

        if 'downloader_threads_limit' in props:  # @TODO (downloader 2.0++): Remove this in a future version
            present.add('downloader_threads_limit')
        if 'downloader_timeout' in props:  # @TODO (downloader 2.0++): Remove this in a future version
            present.add('downloader_timeout')
        if 'downloader_retries' in props:  # @TODO (downloader 2.0++): Remove this in a future version
            present.add('downloader_retries')
        if 'base_path' in props:  # @TODO (downloader 2.0++): Remove this in a future version
            present.add('base_path')

        self.filter: Optional[str]
        if 'filter' in props:
            if not isinstance(props['filter'], str):
                raise DbOptionsValidationException(['filter'])
            present.add('filter')
            self.filter = props['filter'].strip().lower()
        else:
            self.filter = None

        if len(present) != len(props):
            raise DbOptionsValidationException([o for o in props if o not in present])

        self._props = props

    def any(self) -> bool:
        return self.filter is not None

    def unwrap_props(self) -> DbOptionsProps:
        return self._props


class DbOptionsValidationException(Exception):
    def __init__(self, fields) -> None:
        self.fields = fields

    def fields_to_string(self):
        return ', '.join(self.fields)