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

from typing import TypedDict, Optional

from downloader.config import Config
from downloader.db_utils import DbSectionPackage
from downloader.interruptions import Interruptions
from downloader.job_system import JobSystem, Worker, Job
from downloader.jobs.check_db_job import CheckDbJob
from downloader.jobs.jobs_factory import make_transfer_job
from downloader.jobs.load_local_store_sigs_job import LoadLocalStoreSigsJob, local_store_sigs_tag
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReportImpl
from downloader.jobs.worker_context import DownloaderWorkerContext
from downloader.logger import Logger
from downloader.online_checker import OnlineChecker as ProductionOnlineChecker
from test.fake_http_gateway import FakeHttpGateway
from test.fake_importer_implicit_inputs import NetworkState
from test.fake_job_system import ProgressReporterTracker
from test.fake_waiter import NoWaiter
from test.fake_logger import NoLogger
from test.fake_file_system_factory import FileSystemFactory

class OnlineChecker(ProductionOnlineChecker):
    pass