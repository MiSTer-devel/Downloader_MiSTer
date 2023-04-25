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

from downloader.file_downloader import FileDownloaderFactory as ProductionFileDownloaderFactory, LowLevelFileDownloaderFactory, LowLevelFileDownloader, HighLevelFileDownloader
from test.fake_target_path_repository import TargetPathRepository
from test.fake_importer_implicit_inputs import ImporterImplicitInputs, NetworkState, fix_description
from test.fake_file_system_factory import FileSystemFactory, FakeFileSystem
from downloader.logger import NoLogger


class _FakeLowLevelFileDownloaderFactory(LowLevelFileDownloaderFactory):
    def __init__(self, file_system, network_state, target_path_repository):
        self._file_system = file_system
        self._target_path_repository = target_path_repository
        self._network_state = network_state

    def create_low_level_file_downloader(self, high_level) -> LowLevelFileDownloader:
        if isinstance(self._file_system, FakeFileSystem):
            return _FakeLowLevelFileDownloader(self._file_system, self._network_state, self._file_system.state, self._target_path_repository, high_level)
        else:
            return _FakeLowLevelFileDownloaderWithRealFilesystem(self._file_system, self._network_state, None, self._target_path_repository, high_level)


class _FakeLowLevelFileDownloader(LowLevelFileDownloader):
    def __init__(self, file_system, network_state, file_system_state, target_path_repository, high_level):
        self._file_system_state = file_system_state
        self._file_system = file_system
        self._target_path_repository = target_path_repository
        self._high_level = high_level
        self._network_state = network_state
        self._network_errors = []
        self._downloaded_files = []

    def fetch(self, files_to_download, descriptions):
        for file_path, target_path in files_to_download:
            self._download(file_path, target_path, descriptions[file_path])

    def _download(self, file_path, target_path, file_description):
        self._network_state.remote_failures[file_path] = self._network_state.remote_failures.get(file_path, 0)
        self._network_state.remote_failures[file_path] -= 1
        if self._network_state.remote_failures[file_path] > 0:
            self._network_errors.append(file_path)
            return

        if file_path not in self._network_state.storing_problems:
            self._install_file(file_path, file_description, target_path)

        state, _ = self._high_level.validate_download(file_path, file_description['hash'])
        if state == 1:
            self._downloaded_files.append(file_path)
        else:
            self._network_errors.append(file_path)

    def network_errors(self):
        return self._network_errors

    def downloaded_files(self):
        return self._downloaded_files

    def _install_file(self, file_path, file_description, target_path):
        remote_description = self._network_state.remote_files[file_path] if file_path in self._network_state.remote_files else file_description
        fixed_description = fix_description(target_path, remote_description)
        self._file_system_state.add_full_file_path(target_path, fixed_description)


class _FakeLowLevelFileDownloaderWithRealFilesystem(_FakeLowLevelFileDownloader):
    def _install_file(self, _file_path, _file_description, target_path):
        self._file_system.write_file_contents(target_path, 'This is a test file.')


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, file_system_factory=None, config=None, network_state=None):
        self._file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory.from_state(config=config)
        self._is_fake_file_system = isinstance(self._file_system_factory, FileSystemFactory)
        self._network_state = NetworkState() if network_state is None else network_state

    def create(self, config, parallel_update, silent=False, hash_check=True):
        file_system = self._file_system_factory.create_for_config(config)
        target_path_repository = TargetPathRepository(config, file_system)
        low_level_factory = _FakeLowLevelFileDownloaderFactory(file_system, self._network_state, target_path_repository)
        return HighLevelFileDownloader(hash_check, config, file_system, target_path_repository, low_level_factory, NoLogger())

    @staticmethod
    def from_implicit_inputs(implicit_inputs: ImporterImplicitInputs):
        file_system_factory = FileSystemFactory(state=implicit_inputs.file_system_state)
        file_downloader_factory = FileDownloaderFactory(
            file_system_factory=file_system_factory,
            network_state=implicit_inputs.network_state,
            config=implicit_inputs.config,
        )
        return file_downloader_factory, file_system_factory, implicit_inputs.config

    @staticmethod
    def with_remote_files(fsf: FileSystemFactory, config: Dict[str, Any], remote_files: List[Tuple[str, Dict[str, Any]]]):
        return FileDownloaderFactory(file_system_factory=fsf, config=config, network_state=NetworkState(remote_files={
            file_name: {'hash': 'ignore', 'unzipped_json': file_content} for file_name, file_content in remote_files
        }))
