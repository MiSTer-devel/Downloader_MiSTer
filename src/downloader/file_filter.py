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

import re
from pathlib import Path
from typing import List, Optional, Set, Dict, Tuple, Any, Iterable, TypedDict
from abc import ABC, abstractmethod

from downloader.constants import K_FILTER
from downloader.db_entity import DbEntity
from downloader.logger import Logger

FileFolderDesc = Dict[str, Any]
Config = Dict[str, Any]


class FileFoldersHolder(TypedDict):
    files: Dict[str, FileFolderDesc]
    folders: Dict[str, FileFolderDesc]


ZipData = Dict[str, FileFoldersHolder]


filter_part_regex = re.compile("!?[a-z0-9]+[-_a-z0-9.]*$", )


class FilterCalculator(ABC):
    @abstractmethod
    def is_filtered(self, description) -> bool:
        """Returns true if a file must be filtered out according to its description"""


class FilterCalculatorImpl(FilterCalculator):
    def __init__(self, positive, negative):
        self._negative = negative
        self._positive = positive

    def is_filtered(self, description: FileFolderDesc) -> bool:
        tags = description.get('tags', [])

        filtered = len(self._positive) > 0

        for part in self._positive:
            if part in tags:
                filtered = False

        if filtered:
            return True

        for part in self._negative:
            if part in tags:
                filtered = True

        return filtered


class FileFilter:
    def __init__(self, filter_calculator: Optional[FilterCalculator]):
        self._filter_calculator = filter_calculator

    def select_filtered_files(self, db: DbEntity) -> Tuple[DbEntity, ZipData]:
        filtered_zip_data: ZipData = {}

        if self._filter_calculator is None:
            return db, filtered_zip_data

        for file_path, file_desc in list(db.files.items()):
            if self._filter_calculator.is_filtered(file_desc):
                if 'zip_id' in file_desc:
                    self._add_filtered_file_in_zip(filtered_zip_data, file_path, file_desc['zip_id'], file_desc)
                db.files.pop(file_path)

        keep_folders = set()

        for folder_path in reversed(sorted(db.folders.keys(), key=len)):
            if folder_path in keep_folders:
                continue

            folder_desc = db.folders[folder_path]

            if self._filter_calculator.is_filtered(folder_desc):
                if 'zip_id' in folder_desc:
                    self._add_filtered_folder_in_zip(filtered_zip_data, folder_path, folder_desc['zip_id'], folder_desc)
                db.folders.pop(folder_path)
            else:
                for parent in Path(folder_path).parents:
                    keep_folders.add(str(parent))

        return db, filtered_zip_data

    @staticmethod
    def _filtered_zip_data_by_id(filtered_zip_data: ZipData, zip_id: str) -> FileFoldersHolder:
        if zip_id not in filtered_zip_data:
            filtered_zip_data[zip_id] = {'files': {}, 'folders': {}}
        return filtered_zip_data[zip_id]

    def _add_filtered_file_in_zip(self, filtered_zip_data: ZipData, file_path: str, zip_id: str, file_desc: FileFolderDesc):
        zip_desc = self._filtered_zip_data_by_id(filtered_zip_data, zip_id)
        zip_desc['files'][file_path] = file_desc

    def _add_filtered_folder_in_zip(self, filtered_zip_data: ZipData, folder_path: str, zip_id: str, folder_desc: FileFolderDesc):
        zip_desc = self._filtered_zip_data_by_id(filtered_zip_data, zip_id)
        zip_desc['folders'][folder_path] = folder_desc


class FileFilterFactory:
    def __init__(self, logger: Logger):
        self._logger = logger
        self._unused: Set[str] = set()
        self._used: Set[str] = set()

    def create(self, db: DbEntity, config: Config) -> FileFilter:
        return FileFilter(self._create_filter_calculator(db, config))

    def unused_filter_parts(self) -> List[str]:
        return list(self._unused - self._used)

    def _create_filter_calculator(self, db: DbEntity, config: Config) -> Optional[FilterCalculator]:
        if config[K_FILTER] is None or config[K_FILTER] == '':
            self._logger.debug(f'No filter for db {db.db_id}.')
            return None
        this_filter = config[K_FILTER].strip().lower()  # @TODO Remove strip after field is validated in other place
        self._logger.debug(f'Filter for db {db.db_id}: {this_filter}')
        if this_filter == '':
            raise BadFileFilterPartException(this_filter)
        if this_filter == 'all':
            return None
        if this_filter == '!all':
            return AlwaysFilters()

        filter_parts = this_filter.split()
        negative = []
        positive = []

        positive_all = False
        for part in filter_parts:
            this_part = part.strip()

            if not filter_part_regex.match(this_part):
                raise BadFileFilterPartException(this_part)

            is_negative = False
            if this_part[0] == '!':
                is_negative = True
                this_part = this_part[1:]

            this_part = _remove(this_part, ['-', '_'])

            if this_part == 'none':
                raise BadFileFilterPartException('none')

            if this_part == 'all':
                if is_negative:
                    raise BadFileFilterPartException('!all')
                else:
                    positive_all = True

                continue

            used_term = this_part

            if this_part in db.tag_dictionary:
                this_part = db.tag_dictionary[this_part]

            part_in_db = _part_in_db(this_part, db)
            if part_in_db:
                self._used.add(used_term)
            else:
                self._unused.add(this_part)

            if is_negative:
                if part_in_db: negative.append(this_part)
            else:
                positive.append(this_part)

        essential = 'essential'
        if essential in db.tag_dictionary:
            essential = db.tag_dictionary[essential]

        if len(positive) > 0 and essential not in positive and essential not in negative:
            positive.append(essential)

        return FilterCalculatorImpl([] if positive_all else positive, negative)


def _part_in_db(this_part: str, db: DbEntity) -> bool:
    return _part_in_descriptions(this_part, db.files.values())\
        or _part_in_descriptions(this_part, db.folders.values())


def _part_in_descriptions(this_part: str, descriptions: Iterable[Dict[str, Any]]) -> bool:
    for descr in descriptions:
        if 'tags' in descr and this_part in descr['tags']:
            return True

    return False


def _remove(string: str, remove_list: Iterable[str]) -> str:
    for sub in remove_list:
        if sub in string:
            string = string.replace(sub, '')
    return string


class AlwaysFilters(FilterCalculator):
    def is_filtered(self, _) -> bool:
        return True


class BadFileFilterPartException(Exception):
    pass
