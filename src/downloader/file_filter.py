# Copyright (c) 2021 José Manuel Barroso Galindo <theypsilon@gmail.com>

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


filter_part_regex = re.compile("[!]?[a-z]+[-_a-z0-9.]*$", )


class FileFilterFactory:
    def __init__(self):
        self._unused = set()
        self._used = set()

    def create(self, db, config):
        return FileFilter(self._create_filter_calculator(db, config))

    def unused_filter_parts(self):
        return list(self._unused - self._used)

    def _create_filter_calculator(self, db, config):
        if config['filter'] is None:
            return None
        this_filter = config['filter'].strip().lower() # @TODO Remove strip after field is validated in other place
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
            elif not _part_in_db(this_part, db):
                self._unused.add(this_part)
                continue

            if is_negative:
                negative.append(this_part)
            else:
                positive.append(this_part)

            self._used.add(used_term)

        essential = 'essential'
        if essential in db.tag_dictionary:
            essential = db.tag_dictionary[essential]

        if len(positive) > 0 and essential not in positive and essential not in negative:
            positive.append(essential)

        return FilterCalculator([] if positive_all else positive, negative)


def _part_in_db(this_part, db):
    return _part_in_descriptions(this_part, db.files.values())\
        or _part_in_descriptions(this_part, db.folders.values())


def _part_in_descriptions(this_part, descriptions):
    for descr in descriptions:
        if 'tags' in descr and this_part in descr['tags']:
            return True


def _remove(string, remove_list):
    for sub in remove_list:
        if sub in string:
            string = string.replace(sub, '')
    return string


class FileFilter:
    def __init__(self, filter_calculator):
        self._filter_calculator = filter_calculator

    def create_filtered_db(self, db, store):
        if 'filtered_zip_data' in store:
            for zip_id, zip_data in list(store['filtered_zip_data'].items()):
                if zip_id not in db.zips:
                    continue

                for file_path, file_description in zip_data['files'].items():
                    db.files[file_path] = file_description

                for folder_path, folder_description in zip_data['folders'].items():
                    db.folders[folder_path] = folder_description

            store.pop('filtered_zip_data')

        if self._filter_calculator is None:
            return db

        for file_path, file_description in list(db.files.items()):
            if self._filter_calculator.is_filtered(file_description):
                if 'zip_id' in file_description:
                    self._add_file_to_store(store, file_path, file_description)
                db.files.pop(file_path)

        keep_folders = set()

        for folder_path in reversed(list(db.folders.keys())):
            if folder_path in keep_folders:
                continue

            folder_description = db.folders[folder_path]

            if self._filter_calculator.is_filtered(folder_description):
                if 'zip_id' in folder_description:
                    self._add_folder_to_store(store, folder_path, folder_description)
                db.folders.pop(folder_path)
            else:
                for parent in Path(folder_path).parents:
                    keep_folders.add(str(parent))

        return db

    def _add_file_to_store(self, store, file_path, file_description):
        zip_id = file_description['zip_id']
        filtered_zip_data = self._filtered_zip_data_by_id(store, zip_id)
        filtered_zip_data[zip_id]['files'][file_path] = file_description

    def _add_folder_to_store(self, store, folder_path, folder_description):
        zip_id = folder_description['zip_id']
        filtered_zip_data = self._filtered_zip_data_by_id(store, zip_id)
        filtered_zip_data[zip_id]['folders'][folder_path] = folder_description

    def _filtered_zip_data_by_id(self, store, zip_id):
        filtered_zip_data = self._filtered_zip_data(store)
        if zip_id not in filtered_zip_data:
            filtered_zip_data[zip_id] = {'files': {}, 'folders': {}}
        return filtered_zip_data

    def _filtered_zip_data(self, store):
        if 'filtered_zip_data' not in store:
            store['filtered_zip_data'] = {}
        return store['filtered_zip_data']

class FilterCalculator:
    def __init__(self, positive, negative):
        self._negative = negative
        self._positive = positive

    def is_filtered(self, description):
        if 'tags' not in description:
            return False

        filtered = len(self._positive) > 0

        for part in self._positive:
            if part in description['tags']:
                filtered = False

        if filtered:
            return True

        for part in self._negative:
            if part in description['tags']:
                filtered = True

        return filtered


class AlwaysFilters:
    def is_filtered(self, _):
        return True

class BadFileFilterPartException(Exception):
    pass
