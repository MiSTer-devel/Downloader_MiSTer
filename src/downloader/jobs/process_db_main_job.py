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
from typing import Any, Dict, List

from downloader.config import Config, default_config, ConfigDatabaseSection
from downloader.constants import DB_STATE_SIGNATURE_NO_HASH, DB_STATE_SIGNATURE_NO_SIZE
from downloader.db_entity import DbEntity
from downloader.job_system import Job, JobSystem
from downloader.local_store_wrapper import StoreWrapper


@dataclass(eq=False, order=False)
class ProcessDbMainJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())

    db: DbEntity
    store: StoreWrapper
    ini_description: ConfigDatabaseSection
    full_resync: bool
    db_hash: str = field(default=DB_STATE_SIGNATURE_NO_HASH)
    db_size: int = field(default=DB_STATE_SIGNATURE_NO_SIZE)

    def retry_job(self): return None

    # Results
    ignored_zips: List[str] = field(default_factory=list)
    removed_zips: List[str] = field(default_factory=list)
    config: Config = field(default_factory=default_config)
