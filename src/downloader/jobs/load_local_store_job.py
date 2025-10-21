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

from typing import Optional

from downloader.config import Config
from downloader.db_utils import DbSectionPackage
from downloader.job_system import Job, JobSystem
from downloader.jobs.abort_worker import AbortJob
from downloader.local_store_wrapper import LocalStoreWrapper

local_store_tag = 'local_store'

class LoadLocalStoreJob(Job):
    type_id: int = JobSystem.get_job_type_id()
    def __init__(self, db_pkgs: list[DbSectionPackage], config: Config, /) -> None:
        self.db_pkgs = db_pkgs
        self.config = config

        # Results
        self.local_store: Optional[LocalStoreWrapper] = None
        # It will also write on config.file_checking if last_successful_run is not set, but this is deprecated and set to be removed in a future version

    def backup_job(self) -> Optional[Job]: return AbortJob()
