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

from abc import abstractmethod
from typing import Optional

from downloader.error import DownloaderError
from downloader.fail_policy import FailPolicy
from downloader.job_system import Job, Worker
from downloader.logger import Logger


class NilJob(Job): type_id = -1


class JobErrorCtx:
    def __init__(self, logger: Logger, fail_policy: FailPolicy = FailPolicy.FAULT_TOLERANT) -> None:
        self._logger = logger
        self._fail_policy = fail_policy

    def swallow_error(self, error: Optional[Exception], print_error: bool = True) -> None:
        if error is None:
            return

        if self._fail_policy != FailPolicy.FAULT_TOLERANT:
            if self._fail_policy == FailPolicy.FAIL_FAST:
                raise error
            elif (self._fail_policy == FailPolicy.FAULT_TOLERANT_ON_CUSTOM_DOWNLOADER_ERRORS
                  and not isinstance(error, DownloaderError)):
                raise error

        self._logger.debug(error)
        if print_error:
            self._logger.print(f"ERROR: {error}")


class DownloaderWorker(Worker):
    @abstractmethod
    def job_type_id(self) -> int:
        """Returns the type id of the job this worker operates on."""
