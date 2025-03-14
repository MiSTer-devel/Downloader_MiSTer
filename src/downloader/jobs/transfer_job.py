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


import io
from typing import Protocol, Union, Optional, Any

from downloader.job_system import Job


class Transferrer(Protocol):
    def transfer(self) -> Union[str, io.BytesIO]:
        ...

    source: str
    calcs: Optional[dict[str, Any]]
    after_job: Optional[Job]

TransferJob = Union[Transferrer, Job]
