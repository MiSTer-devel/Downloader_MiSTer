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

from typing import List

from downloader.file_downloader import CurlDownloaderAbstract, FileDownloaderFactory as ProductionFileDownloaderFactory
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from downloader.target_path_repository import TargetPathRepository
from test.fake_store_migrator import StoreMigrator
from test.fake_external_drives_repository import ExternalDrivesRepository
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, NetworkState
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger


class _FileDownloaderWithFakeFileSystem(CurlDownloaderAbstract):
    def __init__(self, config, file_system, local_repository, network_state, file_system_state):
        self._file_system_state = file_system_state
        self._file_system = file_system
        self._local_repository = local_repository
        super().__init__(config, self._file_system, self._local_repository, NoLogger(), True, TargetPathRepository(config, self._file_system))
        self._network_state = network_state
        self._run_files = []

    def _run(self, description, target_path: str, file: str) -> None:
        self._run_files.append(file)

        if file not in self._network_state.remote_failures:
            self._network_state.remote_failures[file] = 0

        self._network_state.remote_failures[file] -= 1

        if self._network_state.remote_failures[file] > 0:
            self._errors.add_print_report(file, '')
            return

        if file in self._network_state.remote_files:
            description = self._network_state.remote_files[file]

        if file not in self._network_state.storing_problems:
            self._file_system_state.add_full_file_path(
                self._file_system.download_target_path(target_path),
                self._file_system_state.fix_description(file, description)
            )

        self._http_oks.add(file)

    def _command(self, target_path: str, url: str) -> str:
        return target_path

    def _wait(self) -> None:
        pass

    def run_files(self) -> List[str]:
        return self._run_files


class _FileDownloaderWithRealFileSystem(CurlDownloaderAbstract):
    def __init__(self, config, file_system, local_repository):
        self._file_system = file_system
        self._local_repository = local_repository
        super().__init__(config, self._file_system, self._local_repository, NoLogger(), True, TargetPathRepository(config, self._file_system))

    def _run(self, description, target_path: str, file: str) -> None:
        self._file_system.write_file_contents(target_path, 'This is a test file.')  # Generates a file with hash: test.objects.hash_real_test_file

    def _command(self, target_path: str, url: str) -> str:
        return target_path

    def _wait(self) -> None:
        pass


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, file_system_factory=None, local_repository=None, config=None, network_state=None, external_drives_repository=None):
        self._file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory.from_state(config=config)
        self._is_fake_file_system = isinstance(self._file_system_factory, FileSystemFactory)
        self._local_repository = local_repository
        self._external_drives_repository = external_drives_repository
        self._network_state = NetworkState() if network_state is None else network_state

    def create(self, config, parallel_update, silent=False, hash_check=True):
        file_system = self._file_system_factory.create_for_config(config)
        external_drives_repository = self._external_drives_repository if self._external_drives_repository is not None else ExternalDrivesRepository(file_system=file_system)
        local_repository = self._local_repository if self._local_repository is not None else ProductionLocalRepository(config, NoLogger(), file_system, StoreMigrator(), external_drives_repository)
        if self._is_fake_file_system:
            return _FileDownloaderWithFakeFileSystem(config, file_system, local_repository, self._network_state, self._file_system_factory._state)
        else:
            return _FileDownloaderWithRealFileSystem(config, file_system, local_repository)

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs):
        file_system_factory = FileSystemFactory(state=implicit_inputs.file_system_state)
        file_downloader_factory = FileDownloaderFactory(
            file_system_factory=file_system_factory,
            network_state=implicit_inputs.network_state,
            config=implicit_inputs.config,
        )
        return file_downloader_factory, file_system_factory, implicit_inputs.config

