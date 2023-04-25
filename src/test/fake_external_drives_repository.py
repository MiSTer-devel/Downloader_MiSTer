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
from downloader.external_drives_repository import ExternalDrivesRepository as ProductionExternalDrivesRepository
from test.fake_file_system_factory import FileSystemFactory
from downloader.logger import NoLogger


class ExternalDrivesRepository(ProductionExternalDrivesRepository):
    def __init__(self, file_system=None):
        super().__init__(file_system if file_system is not None else FileSystemFactory().create_for_system_scope(), NoLogger())

    def _retrieve_connected_drives_list(self):
        return self._drives_from_fs()


class ExternalDrivesRepositoryStub:
    def __init__(self, drives): self._drives = drives
    def connected_drives(self): return self._drives
    def connected_drives_except_base_path_drives(self, _): return self._drives


class ExternalDrivesRepositoryFactoryStub:
    def __init__(self, drives): self._drives = drives
    def create(self, _1, _2): return ExternalDrivesRepositoryStub(self._drives)
