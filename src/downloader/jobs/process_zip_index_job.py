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

from dataclasses import field, dataclass
from typing import Any, Optional

from downloader.config import Config, ConfigDatabaseSection
from downloader.db_entity import DbEntity, ZipIndexEntity
from downloader.file_filter import FileFoldersHolder
from downloader.free_space_reservation import Partition
from downloader.job_system import Job, JobSystem
from downloader.local_store_wrapper import StoreFragmentDrivePaths, ReadOnlyStoreAdapter
from downloader.path_package import PathPackage


@dataclass(eq=False, order=False)
class ProcessZipIndexJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    # Inputs
    db: DbEntity
    store: ReadOnlyStoreAdapter
    config: Config
    zip_id: str
    ini_description: ConfigDatabaseSection
    zip_description: dict[str, Any]
    zip_index: ZipIndexEntity
    has_new_zip_summary: bool

    def retry_job(self): return None

    # Results
    result_zip_index: StoreFragmentDrivePaths
    filtered_data: Optional[FileFoldersHolder] = field(default=None)

    present_not_validated_files: list[PathPackage] = field(default_factory=list)
    present_validated_files: list[PathPackage] = field(default_factory=list)
    skipped_updated_files: list[PathPackage] = field(default_factory=list)
    non_duplicated_files: list[PathPackage] = field(default_factory=list)
    duplicated_files: list[str] = field(default_factory=list)

    installed_folders: list[PathPackage] = field(default_factory=list)
    removed_folders: list[PathPackage] = field(default_factory=list)  #  @TODO: Why there is removed_folders AND directories_to_remove?

    directories_to_remove: list[PathPackage] = field(default_factory=list)
    files_to_remove: list[PathPackage] = field(default_factory=list)

    repeated_store_presence: set[str] = field(default_factory=set)

    # Failure results
    full_partitions: list[tuple[Partition, int]] = field(default_factory=list)
    failed_files_no_space: list[PathPackage] = field(default_factory=list)
    failed_folders: list[str] = field(default_factory=list)

    # Success & Failure results
    summary_download_failed: Optional[str] = field(default=None)
