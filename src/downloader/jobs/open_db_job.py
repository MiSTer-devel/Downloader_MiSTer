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

from dataclasses import field, dataclass

from downloader.config import ConfigDatabaseSection
from downloader.job_system import Job, JobSystem
from downloader.jobs.load_local_store_job import LoadLocalStoreJob
from downloader.jobs.load_local_store_fingerprints_job import LoadLocalStoreFingerprintsJob
from downloader.jobs.transfer_job import TransferJob


@dataclass(eq=False, order=False)
class OpenDbJob(Job):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())
    transfer_job: TransferJob # Job & Transferrer @TODO: Python 3.10
    section: str
    ini_description: ConfigDatabaseSection
    load_local_store_fingerprints_job: LoadLocalStoreFingerprintsJob
    load_local_store_job: LoadLocalStoreJob

    def retry_job(self): return self.transfer_job
    @property
    def priority(self) -> bool: return True

    # Results
    skipped: bool = field(default=False)
    filter_terms_from_ini: set[str] = field(default_factory=set)
