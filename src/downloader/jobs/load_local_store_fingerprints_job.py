# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from downloader.job_system import Job, JobSystem
from downloader.local_store_wrapper import DbStateFingerprint

local_store_fingerprints_tag = 'local_store_fingerprints'

class LoadLocalStoreFingerprintsJob(Job):
    type_id: int = JobSystem.get_job_type_id()
    def __init__(self, /) -> None:
        # Results
        self.local_store_fingerprints: Optional[dict[str, DbStateFingerprint]] = None
        self.available_external_store_fingerprints: dict[str, set[str]] = {}
        self.external_store_fingerprints_supported: bool = False

    def backup_job(self) -> Optional[Job]: return None
    def retry_job(self) -> Optional['Job']: return None
    @property
    def priority(self) -> bool: return True
