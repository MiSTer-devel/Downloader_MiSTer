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

from typing import Set, TypedDict, NotRequired, Dict, Any

from downloader.other import test_only


class DbOptionsProps(TypedDict):
    downloader_threads_limit: NotRequired[int]
    downloader_timeout: NotRequired[int]
    downloader_retries: NotRequired[int]
    filter: NotRequired[str]


class DbOptions:
    def __init__(self, props: DbOptionsProps):
        present: Set[str] = set()

        if 'downloader_threads_limit' in props:
            if not isinstance(props['downloader_threads_limit'], int) or props['downloader_threads_limit'] < 1:
                raise DbOptionsValidationException(['downloader_threads_limit'])
            present.add('downloader_threads_limit')
        if 'downloader_timeout' in props:
            if not isinstance(props['downloader_timeout'], int) or props['downloader_timeout'] < 1:
                raise DbOptionsValidationException(['downloader_timeout'])
            present.add('downloader_timeout')
        if 'downloader_retries' in props:
            if not isinstance(props['downloader_retries'], int) or props['downloader_retries'] < 1:
                raise DbOptionsValidationException(['downloader_retries'])
            present.add('downloader_retries')
        if 'filter' in props:
            if not isinstance(props['filter'], str):
                raise DbOptionsValidationException(['filter'])
            present.add('filter')

        if len(present) != len(props):
            raise DbOptionsValidationException([o for o in props if o not in present])

        self._props = props

    def items(self):
        return self._props.items()

    def unwrap_props(self) -> DbOptionsProps:
        return self._props

    def apply_to_config(self, config: Dict[str, Any]):
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