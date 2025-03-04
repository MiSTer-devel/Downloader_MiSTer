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

from dataclasses import field, dataclass
from enum import IntEnum, auto, unique
from typing import Dict, Any, List, Optional

from downloader.db_entity import DbEntity
from downloader.file_filter import FileFoldersHolder, Config
from downloader.job_system import Job, JobSystem
from downloader.jobs.transferrer_job import TransferrerJob
from downloader.path_package import PathPackage
from downloader.local_store_wrapper import StoreWrapper


@unique
class ZipKind(IntEnum):
    EXTRACT_ALL_CONTENTS = auto()
    EXTRACT_SINGLE_FILES = auto()


@dataclass(eq=False, order=False)
class OpenZipContentsJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    db: DbEntity
    store: StoreWrapper
    ini_description: Dict[str, Any]
    full_resync: bool
    config: Config

    zip_id: str
    zip_kind: ZipKind
    zip_description: Dict[str, Any]
    target_folder: Optional[PathPackage]
    total_amount_of_files_in_zip: int
    files_to_unzip: List[PathPackage]
    recipient_folders: List[PathPackage]
    transfer_job: TransferrerJob # Job & Transferrer @TODO: Python 3.10
    action_text: str
    zip_base_files_url: str
    filtered_data: FileFoldersHolder

    def retry_job(self): return self.transfer_job

    # Results
    downloaded_files: List[PathPackage] = field(default_factory=list)
    validated_files: List[PathPackage] = field(default_factory=list)
    failed_files: List[PathPackage] = field(default_factory=list)
    directories_to_remove: List[PathPackage] = field(default_factory=list)
    files_to_remove: List[PathPackage] = field(default_factory=list)
