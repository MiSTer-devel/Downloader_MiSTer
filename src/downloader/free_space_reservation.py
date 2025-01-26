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

import os
import threading
from typing import Dict, List, Any, Tuple, Optional, Iterable, Protocol

from downloader.config import Config
from downloader.constants import STORAGE_PATHS_PRIORITY_SEQUENCE, K_MINIMUM_SYSTEM_FREE_SPACE_MB, K_BASE_SYSTEM_PATH, K_MINIMUM_EXTERNAL_FREE_SPACE_MB
from downloader.logger import Logger
from downloader.path_package import PathPackage


class FreeSpaceReservation(Protocol):
    # @deprecated
    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        """Reserve space for a file that will be downloaded later"""

    def reserve_space_for_file_pkgs(self, file_pkgs: Iterable[PathPackage]) -> Tuple[bool, List[Tuple['Partition', int]]]:
        """Reserve space for a file that will be downloaded later"""

    # @deprecated
    def release_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        """Release space previously reserved for a file that won't be downloaded later"""

    # @deprecated
    def get_full_partitions(self) -> List['FullPartition']:
        """Get a list of partitions that are full"""

    def free_space(self) -> Dict[str, int]:
        """Get a dictionary with the free space in each partition"""


class FullPartition:
    def __init__(self, partition_path: str, files: List[str]):
        self.partition_path = partition_path
        self.files = files


class LinuxFreeSpaceReservation(FreeSpaceReservation):
    def __init__(self, logger: Logger, config: Config, partitions: Optional[Dict[str, 'Partition']] = None):
        self._logger = logger
        self._config = config
        self._partitions: Dict[str, Partition] = partitions or {}
        self._lock = threading.Lock()

    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        partition = self._get_partition_for_file(full_file_path)
        partition.reserve_space(full_file_path, file_description)

    def reserve_space_for_file_pkgs(self, file_pkgs: Iterable[PathPackage]) -> Tuple[bool, List[Tuple['Partition', int]]]:
        with self._lock:
            partitions_reservations: Dict[str, int] = {}
            for file_pkg in file_pkgs:
                partition = self._get_partition_for_file(file_pkg.full_path)
                if partition.path not in partitions_reservations:
                    partitions_reservations[partition.path] = 0
                partitions_reservations[partition.path] += partition.file_size(file_pkg.description['size'])

            full_partitions: List[Tuple[Partition, int]] = []
            for partition_path, size in partitions_reservations.items():
                remaining_space = self._partitions[partition_path].check_potential_remaining_space(size)
                if remaining_space <= self._partitions[partition_path].min_space:
                    full_partitions.append((self._partitions[partition_path], size))

            if len(full_partitions) > 0:
                return False, full_partitions

            for partition_path, size in partitions_reservations.items():
                self._partitions[partition_path].reserve_raw_space(size)

            return True, []
        
    def release_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        partition = self._get_partition_for_file(full_file_path)
        partition.release_space(full_file_path, file_description)

    def get_full_partitions(self) -> List[FullPartition]:
        return [FullPartition(path, p.files) for path, p in self._partitions.items() if p.is_full()]

    def free_space(self) -> Dict[str, int]:
        return {partition_path: partition.remaining_space for partition_path, partition in self._partitions.items()}

    def _get_partition_for_file(self, file_path) -> 'Partition':
        partition_path = self._get_partition_path_from_file(file_path)
        if partition_path not in self._partitions:
            self._partitions[partition_path] = self._make_partition(partition_path)
        return self._partitions[partition_path]

    def _get_partition_path_from_file(self, file_path) -> str:
        for path in STORAGE_PATHS_PRIORITY_SEQUENCE:
            if file_path.startswith(path):
                return path

        self._logger.print(f'Could not find partition for file {file_path}')
        return STORAGE_PATHS_PRIORITY_SEQUENCE[0]

    def _make_partition(self, partition_path) -> 'Partition':
        statvfs = os.statvfs(partition_path)
        free_space = statvfs.f_frsize * statvfs.f_bavail
        block_size = statvfs.f_frsize
        self._logger.debug(f'Partition {partition_path} has {free_space} bytes available [{block_size} bytes per block]')
        return Partition(available_space=free_space, min_space=partition_min_space(self._config, partition_path), block_size=block_size, path=partition_path)


def partition_min_space(config, path: str) -> int:
    return config[K_MINIMUM_SYSTEM_FREE_SPACE_MB] if path == config[K_BASE_SYSTEM_PATH] else config[K_MINIMUM_EXTERNAL_FREE_SPACE_MB]


class UnlimitedFreeSpaceReservation(FreeSpaceReservation):
    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None: pass
    def reserve_space_for_file_pkgs(self, file_pkgs: Iterable[PathPackage]) -> Tuple[bool, List[Tuple['Partition', int]]]: return True, []
    def release_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None: pass
    def get_full_partitions(self) -> List[FullPartition]: return []
    def free_space(self) -> Dict[str, int]: return {}


class Partition:
    def __init__(self, available_space: int, min_space: int, block_size: int, path: str = ""):
        self.path = path
        self.available_space = available_space
        self.min_space = min_space * 1024 * 1024
        self._block_size = block_size
        self._reserved_space = 0
        self.files: List[str] = []

    def reserve_space(self, file_path: str, file_description: Dict[str, Any]) -> None:
        self._reserved_space += file_size_on_disk(int(file_description['size']), self._block_size)
        self.files.append(file_path)

    def reserve_raw_space(self, size: int) -> None:
        self._reserved_space += size

    def release_space(self, file_path: str, file_description: Dict[str, Any]) -> None:
        self._reserved_space -= file_size_on_disk(int(file_description['size']), self._block_size)
        self.files.remove(file_path)

    def check_potential_remaining_space(self, size: int) -> int:
        return self.available_space - self._reserved_space - size

    def fits_raw_size(self, size: int) -> bool:
        return self.check_potential_remaining_space(size) <= self.min_space

    def is_full(self) -> bool:
        return self.remaining_space <= self.min_space

    def file_size(self, size: int) -> int:
        return file_size_on_disk(size, self._block_size)

    @property
    def remaining_space(self) -> int:
        return self.available_space - self._reserved_space


def file_size_on_disk(size: int, block_size: int) -> int:
    blocks = size // block_size
    remainder = size % block_size
    return size if remainder == 0 else (blocks + 1) * block_size
