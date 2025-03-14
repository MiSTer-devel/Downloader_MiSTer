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
from typing import Dict, Any, Optional

from downloader.config import Config, ConfigDatabaseSection
from downloader.db_entity import DbEntity
from downloader.job_system import Job, JobSystem
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.transfer_job import TransferJob
from downloader.local_store_wrapper import StoreWrapper


@dataclass(eq=False, order=False)
class OpenZipSummaryJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    db: DbEntity
    store: StoreWrapper
    zip_id: str
    ini_description: ConfigDatabaseSection
    zip_description: Dict[str, Any]
    full_resync: bool
    config: Config
    transfer_job: TransferJob # Job & Transferrer  @TODO: Python 3.10
    backup: Optional[ProcessZipIndexJob]

    def retry_job(self) -> Optional[Job]:
        return self.transfer_job  # type: ignore[return-value]

    def backup_job(self) -> Optional[Job]:
        return self.backup
