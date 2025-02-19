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
import io
from typing import Any, Dict, Optional, Union

from downloader.job_system import Job, JobSystem
from downloader.jobs.fetch_data_job import Transferrer
from downloader.jobs.get_file_job import GetFileJob


@dataclass(eq=False, order=False)
class ValidateFileJob(Job, Transferrer):
    type_id: int = field(init=False, default=JobSystem.get_job_type_id())
    target_file_path: str
    description: Dict[str, Any]
    info: str
    temp_path: str
    get_file_job: GetFileJob
    backup_path: Optional[str] = None
    after_job: Optional[Job] = None
    priority: bool = True

    def retry_job(self) -> Optional[Job]:
        return self.get_file_job

    def backup_job(self) -> Optional[Job]:
        return None if self.after_job is None else self.after_job.backup_job()

    def transfer(self) -> Union[str, tuple[str, io.BytesIO]]:
        return self.target_file_path
