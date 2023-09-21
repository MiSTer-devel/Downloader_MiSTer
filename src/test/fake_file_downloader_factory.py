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

from typing import Dict, Any, List, Tuple

from downloader.file_downloader import FileDownloaderFactory as ProductionFileDownloaderFactory
from downloader.job_system import JobSystem
from downloader.jobs.reporters import FileDownloadProgressReporter
from test.fake_http_gateway import FakeHttpGateway
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, NetworkState, FileSystemState
from test.fake_file_system_factory import FileSystemFactory
from downloader.logger import NoLogger
from test.fake_waiter import NoWaiter


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, file_system_factory=None, state=None, config=None, network_state=None, file_download_reporter=None, job_system=None, http_gateway=None):
        state = state if state is not None else FileSystemState(config=config)
        file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory(state=state, config=state.config)
        network_state = NetworkState() if network_state is None else network_state
        file_download_reporter = file_download_reporter if file_download_reporter is not None else FileDownloadProgressReporter(NoLogger(), NoWaiter())
        job_system = job_system if job_system is not None else JobSystem(file_download_reporter, max_threads=1)
        http_gateway = http_gateway if http_gateway is not None else FakeHttpGateway(state.config, network_state)
        super().__init__(
            file_system_factory=file_system_factory,
            waiter=NoWaiter(),
            logger=NoLogger(),
            job_system=job_system,
            file_download_reporter=file_download_reporter,
            http_gateway=http_gateway
        )

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs):
        file_system_factory = FileSystemFactory(state=implicit_inputs.file_system_state)
        file_downloader_factory = FileDownloaderFactory(
            file_system_factory=file_system_factory,
            network_state=implicit_inputs.network_state,
            state=implicit_inputs.file_system_state,
        )
        return file_downloader_factory, file_system_factory, implicit_inputs.config

    @staticmethod
    def with_remote_files(fsf: FileSystemFactory, config: Dict[str, Any], remote_files: List[Tuple[str, Dict[str, Any]]]):
        return FileDownloaderFactory(file_system_factory=fsf, config=config, network_state=NetworkState(remote_files={
            file_name: {'hash': 'ignore', 'unzipped_json': file_content} for file_name, file_content in remote_files
        }))
