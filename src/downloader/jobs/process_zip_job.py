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
from typing import Any, Dict

from downloader.db_entity import DbEntity
from downloader.job_system import Job, JobSystem
from downloader.jobs.index import Index
from downloader.local_store_wrapper import StoreWrapper, StoreFragmentDrivePaths


@dataclass(eq=False)
class ProcessZipJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    db: DbEntity
    store: StoreWrapper
    config: Dict[str, Any]
    zip_id: str
    ini_description: Dict[str, Any]
    zip_description: Dict[str, Any]
    zip_index: Index
    has_new_zip_index: bool
    full_resync: bool

    # results
    result_zip_index: StoreFragmentDrivePaths

    def retry_job(self): return None
