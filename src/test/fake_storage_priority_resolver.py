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
from downloader.storage_priority_resolver import StoragePriorityResolver as ProductionCorePathResolverFactory
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_file_system_factory import FileSystemFactory


def make_production_storage_priority_resolver_factory(file_system_factory):
    return ProductionCorePathResolverFactory(file_system_factory, ExternalDrivesRepository(file_system=file_system_factory.create_for_system_scope()))


class StoragePriorityResolverFactory(ProductionCorePathResolverFactory):
    def __init__(self, file_system_factory=None, external_drives_repository=None):
        file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory()
        external_drives_repository = external_drives_repository if external_drives_repository is not None else ExternalDrivesRepository(file_system=file_system_factory.create_for_system_scope())
        super().__init__(file_system_factory, external_drives_repository)
