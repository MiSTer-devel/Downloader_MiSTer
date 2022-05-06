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
from downloader.path_resolver import PathResolverFactory as ProductionPathResolverFactory
from test.fake_file_system_factory import FileSystemFactory
from test.fake_storage_priority_resolver import StoragePriorityResolverFactory, make_production_storage_priority_resolver_factory


def make_production_path_resolver_factory(file_system_factory):
    return ProductionPathResolverFactory(make_production_storage_priority_resolver_factory(file_system_factory), {})


class PathResolverFactory(ProductionPathResolverFactory):
    def __init__(self, storage_priority_resolver_factory=None, os_name=None, file_system_factory=None, path_dictionary=None):
        storage_priority_resolver_factory = storage_priority_resolver_factory if storage_priority_resolver_factory is not None else StoragePriorityResolverFactory(file_system_factory=file_system_factory)
        path_dictionary = path_dictionary if path_dictionary is not None else {}
        super().__init__(storage_priority_resolver_factory=storage_priority_resolver_factory, path_dictionary=path_dictionary, os_name=os_name)

    @staticmethod
    def from_file_system_state(state):
        return PathResolverFactory(file_system_factory=FileSystemFactory(state=state), path_dictionary=state.path_dictionary)
