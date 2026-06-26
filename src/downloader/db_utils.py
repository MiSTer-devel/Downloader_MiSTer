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


from dataclasses import dataclass

from downloader.config import Config, ConfigDatabaseSection, FileChecking
from downloader.constants import DB_STATE_FINGERPRINT_NO_HASH, DB_STATE_FINGERPRINT_NO_SIZE, \
    DB_STATE_FINGERPRINT_NO_TIMESTAMP, K_FILTER
from downloader.db_entity import DbEntity
from downloader.local_store_wrapper import DbStateFingerprint


@dataclass
class DbSectionPackage:
    db_id: str
    section: ConfigDatabaseSection


def sorted_db_sections(config: Config) -> list[tuple[str, ConfigDatabaseSection]]:
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

    if db.default_options.filter is not None:
        if 'filter' not in input_config['user_defined_options'] or '[mister]' in db.default_options.filter:
            result['filter'] = db.default_options.filter

    if 'options' in ini_description and ini_description['options'].filter is not None:
        result['filter'] = ini_description['options'].filter

    if result['filter'] is not None:
        result['filter'] = result['filter'].lower()
        if '[mister]' in result['filter']:
            mister_filter = '' if 'filter' not in input_config or input_config['filter'] is None else input_config['filter'].lower()
            result['filter'] = result['filter'].lower().replace('[mister]', mister_filter).strip()

    return result


def filter_terms_from_ini(input_config: Config, ini_description: ConfigDatabaseSection) -> set[str]:
    if 'options' in ini_description and ini_description['options'].filter is not None:
        return _filter_terms(_expand_mister_filter(ini_description['options'].filter, _mister_filter(input_config)))

    if K_FILTER in input_config['user_defined_options']:
        return _filter_terms(_mister_filter(input_config))

    return set()


def _expand_mister_filter(filter_value: str, mister_filter: str) -> str:
    return filter_value.lower().replace('[mister]', mister_filter.lower()).strip()


def _mister_filter(config: Config) -> str:
    return '' if K_FILTER not in config or config[K_FILTER] is None else config[K_FILTER].lower()


def _filter_terms(filter_value: str) -> set[str]:
    terms = set()
    for part in filter_value.lower().split():
        this_part = part.strip()
        if this_part == '' or this_part == '[mister]':
            continue
        if this_part[0] == '!':
            this_part = this_part[1:]
        this_part = this_part.replace('-', '').replace('_', '')
        if this_part != '' and this_part != 'all':
            terms.add(this_part)
    return terms


def can_skip_db(file_checking: FileChecking, figp: DbStateFingerprint, db_hash: str, db_size: int, user_filter: str) -> bool:
    return file_checking == FileChecking.FASTEST \
        and figp['hash'] == db_hash and figp['hash'] != DB_STATE_FINGERPRINT_NO_HASH \
        and figp['size'] == db_size and figp['size'] != DB_STATE_FINGERPRINT_NO_SIZE \
        and figp['filter'] == user_filter
# Not really needed because collisions are very improbable, but if we are paranoid we can add: and figp['timestamp'] == db.timestamp and figp['timestamp'] != DB_STATE_FINGERPRINT_NO_TIMESTAMP \
