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

import io
import os
from pathlib import Path
from typing import Any, Optional, Protocol, Union

from downloader.file_system import FsError
from downloader.job_system import Job, JobSystem


class Transferer(Protocol):
    def transfer(self) -> Union[str, tuple[str, io.BytesIO]]:
        ...

class CopyDataJob(Job, Transferer):
    __slots__ = ('_tags', 'source', 'valid_hash', 'valid_size', 'after_job', 'data')
    type_id: int = JobSystem.get_job_type_id()
    def __init__(self, source: str, description: dict[str, Any],/):
        self.source = source
        self.description = description

        # Next job
        self.after_job: Optional[Job] = None
        self.backup: Optional[Job] = None

        # Results
        self.data: Optional[io.BytesIO] = None

    def transfer(self) -> Union[str, tuple[str, io.BytesIO]]:
        return (self.source, self.data)

    def backup_job(self) -> Optional[Job]:
        return self.backup
