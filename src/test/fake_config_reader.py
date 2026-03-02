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

import configparser
from typing import Optional

from downloader.config_reader import ConfigReader as ProductionConfigReader
from test.fake_logger import NoLogger
from test.objects import default_env


class ConfigReader(ProductionConfigReader):
    def __init__(self, env=None, file_contents: Optional[dict] = None):
        super().__init__(NoLogger(), env or default_env(), 0)
        self._file_contents = file_contents

    def _load_ini_config(self, config_path) -> configparser.ConfigParser:
        if self._file_contents is None:
            return super()._load_ini_config(config_path)
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        ini_config.read_string(self._file_contents.get(config_path, ''))
        return ini_config

    def _discover_drop_in_files(self, config_path: str) -> list[str]:
        if self._file_contents is None:
            return super()._discover_drop_in_files(config_path)
        base_name = config_path.rsplit('/', 1)[0] if '/' in config_path else ''
        prefix = (base_name + '/') if base_name else ''

        d_files = []
        star_files = []
        for path in self._file_contents:
            if path == config_path:
                continue
            rel = path[len(prefix):] if path.startswith(prefix) else path
            basename = rel.rsplit('/', 1)[-1]
            if not basename.endswith('.ini') or basename.startswith('.'):
                continue
            if rel.startswith('downloader/'):
                d_files.append(path)
            elif rel.startswith('downloader_'):
                star_files.append(path)

        return sorted(d_files) + sorted(star_files)

    def _load_drop_in_ini(self, drop_in_path: str) -> configparser.ConfigParser:
        if self._file_contents is None:
            return super()._load_drop_in_ini(drop_in_path)
        ini_config = configparser.ConfigParser(inline_comment_prefixes=(';', '#'))
        ini_config.read_string(self._file_contents.get(drop_in_path, ''))
        return ini_config
