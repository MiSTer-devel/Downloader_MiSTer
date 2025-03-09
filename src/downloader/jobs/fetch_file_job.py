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

from typing import Optional, Union
import io

from downloader.job_system import Job, JobSystem
from downloader.jobs.transfer_job import Transferrer
from downloader.path_package import PathPackage


class FetchFileJob(Job, Transferrer):
    __slots__ = ('_tags', 'source', 'already_exists', 'pkg', 'db_id', 'after_job')
    type_id: int = JobSystem.get_job_type_id()
    def __init__(self, source: str, already_exists: bool, pkg: Optional[PathPackage], db_id: Optional[str], /):
        self.source = source
        self.already_exists = already_exists
        self.pkg = pkg
        self.db_id = db_id

        # Next job
        self.after_job: Optional[Job] = None

    def transfer(self) -> Union[str, io.BytesIO]:
        return self.pkg.full_path

    def backup_job(self) -> Optional[Job]:
        return None if self.after_job is None else self.after_job.backup_job()
