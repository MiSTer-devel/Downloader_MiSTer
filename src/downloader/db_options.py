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

from downloader.other import test_only


@unique
class DbOptionsKind(Enum):
    DEFAULT_OPTIONS = 1
    INI_SECTION = 2


class DbOptions:
    def __init__(self, props, kind: DbOptionsKind):
        present = set()

        if kind == DbOptionsKind.INI_SECTION:
            if 'base_path' in props:
                if not isinstance(props['base_path'], str):
                    raise DbOptionsValidationException(['base_path'])
                present.add('base_path')
        elif kind == DbOptionsKind.DEFAULT_OPTIONS:
            pass
        else:
            raise ValueError("Invalid props kind: " + str(kind))

        if 'parallel_update' in props:
            if not isinstance(props['parallel_update'], bool):
                raise DbOptionsValidationException(['parallel_update'])
            present.add('parallel_update')
        if 'update_linux' in props:
            if not isinstance(props['update_linux'], bool):
                raise DbOptionsValidationException(['update_linux'])
            present.add('update_linux')
        if 'downloader_size_mb_limit' in props:
            if not isinstance(props['downloader_size_mb_limit'], int) or props['downloader_size_mb_limit'] < 1:
                raise DbOptionsValidationException(['downloader_size_mb_limit'])
            present.add('downloader_size_mb_limit')
        if 'downloader_process_limit' in props:
            if not isinstance(props['downloader_process_limit'], int) or props['downloader_process_limit'] < 1:
                raise DbOptionsValidationException(['downloader_process_limit'])
            present.add('downloader_process_limit')
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
        if 'url_safe_characters' in props:
            if not isinstance(props['url_safe_characters'], dict):
                raise DbOptionsValidationException(['url_safe_characters'])
            present.add('url_safe_characters')

        if len(present) != len(props):
            raise DbOptionsValidationException([o for o in props if o not in present])

        self._props = props

    def items(self):
        return self._props.items()

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