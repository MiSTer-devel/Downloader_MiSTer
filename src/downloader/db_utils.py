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


from dataclasses import dataclass
from typing import List, Tuple

from downloader.config import Config, ConfigDatabaseSection
from downloader.db_entity import DbEntity
from downloader.local_store_wrapper import StoreWrapper


@dataclass
class DbSectionPackage:
    db_id: str
    section: ConfigDatabaseSection
    store: StoreWrapper
 

def sorted_db_sections(config: Config) -> List[Tuple[str, ConfigDatabaseSection]]:
    result = []
    first = None
    for db_id, db_section in config['databases'].items():
        if db_id == config['default_db_id']:
            first = (db_id, db_section)
        else:
            result.append((db_id, db_section))

    if first is not None:
        result = [first, *result]

    return result


def build_db_config(input_config: Config, db: DbEntity, ini_description: ConfigDatabaseSection) -> Config:
    result = input_config.copy()

    for key, option in db.default_options.items():
        if key not in input_config['user_defined_options'] or (key == 'filter' and '[mister]' in option.lower()):
            result[key] = option  # type: ignore[literal-required]

    if 'options' in ini_description:
        result.update(ini_description['options'].unwrap_props())

    if result['filter'] is not None:
        result['filter'] = result['filter'].lower()
        if '[mister]' in result['filter']:
            mister_filter = '' if 'filter' not in input_config or input_config['filter'] is None else input_config['filter'].lower()
            result['filter'] = result['filter'].lower().replace('[mister]', mister_filter).strip()

    return result
