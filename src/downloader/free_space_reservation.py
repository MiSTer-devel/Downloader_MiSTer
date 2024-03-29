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

import abc
import os
from typing import Dict, List, Any

from downloader.constants import STORAGE_PATHS_PRIORITY_SEQUENCE, K_MINIMUM_SYSTEM_FREE_SPACE_MB, K_BASE_SYSTEM_PATH, K_MINIMUM_EXTERNAL_FREE_SPACE_MB
from downloader.logger import Logger


class FreeSpaceReservation(abc.ABC):
    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        """Reserve space for a file that will be downloaded later"""

    def get_full_partitions(self) -> List['FullPartition']:
        """Get a list of partitions that are full"""

    def free_space(self) -> Dict[str, int]:
        """Get a dictionary with the free space in each partition"""


class FullPartition:
    def __init__(self, partition_path: str, files: List[str]):
        self.partition_path = partition_path
        self.files = files


class LinuxFreeSpaceReservation(FreeSpaceReservation):
    def __init__(self, logger: Logger, config: Dict[str, Any], partitions: Dict[str, 'Partition'] = None):
        self._logger = logger
        self._config = config
        self._partitions: Dict[str, Partition] = partitions or {}

    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None:
        partition = self._get_partition_for_file(full_file_path)
        partition.reserve_space(full_file_path, file_description)

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
        return Partition(available_space=free_space, min_space=partition_min_space(self._config, partition_path), block_size=block_size)


def partition_min_space(config, path: str) -> int:
    return config[K_MINIMUM_SYSTEM_FREE_SPACE_MB] if path == config[K_BASE_SYSTEM_PATH] else config[K_MINIMUM_EXTERNAL_FREE_SPACE_MB]


class UnlimitedFreeSpaceReservation(abc.ABC):
    def reserve_space_for_file(self, full_file_path: str, file_description: Dict[str, Any]) -> None: pass
    def get_full_partitions(self) -> List[FullPartition]: return []
    def free_space(self) -> Dict[str, int]: return {}


class Partition:
    def __init__(self, available_space: int, min_space: int, block_size: int):
        self.available_space = available_space
        self.min_space = min_space * 1024 * 1024
        self._block_size = block_size
        self._reserved_space = 0
        self.files: List[str] = []

    def reserve_space(self, file_path: str, file_description: Dict[str, Any]) -> None:
        self._reserved_space += file_size_on_disk(int(file_description['size']), self._block_size)
        self.files.append(file_path)

    def is_full(self) -> bool:
        return self.remaining_space <= self.min_space

    @property
    def remaining_space(self) -> int:
        return self.available_space - self._reserved_space


def file_size_on_disk(size: int, block_size: int) -> int:
    blocks = size // block_size
    remainder = size % block_size
    return size if remainder == 0 else (blocks + 1) * block_size
