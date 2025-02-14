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

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

from downloader.config import Config
from downloader.db_entity import DbEntity
from downloader.free_space_reservation import Partition
from downloader.job_system import Job, JobSystem
from downloader.jobs.index import Index
from downloader.local_store_wrapper import StoreWrapper
from downloader.path_package import PathPackage, RemovedCopy


@dataclass(eq=False, order=False)
class ProcessIndexJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    db: DbEntity
    store: StoreWrapper
    ini_description: Dict[str, Any]
    index: Index
    full_resync: bool
    config: Config
    from_zip: bool = False

    def retry_job(self): return None

    # Results
    present_not_validated_files: List[PathPackage] = field(default_factory=list)
    present_validated_files: List[PathPackage] = field(default_factory=list)
    skipped_updated_files: List[PathPackage] = field(default_factory=list)
    removed_copies: List[RemovedCopy] = field(default_factory=list)
    installed_folders: List[PathPackage] = field(default_factory=list)
    directories_to_remove: List[PathPackage] = field(default_factory=list)
    files_to_remove: List[PathPackage] = field(default_factory=list)

    # Failure results
    full_partitions: List[Tuple[Partition, int]] = field(default_factory=list)
    failed_files_no_space: List[PathPackage] = field(default_factory=list)
    failed_folders: List[str] = field(default_factory=list)