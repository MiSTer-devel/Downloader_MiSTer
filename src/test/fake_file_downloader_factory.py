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

from downloader.config import default_config
from downloader.file_downloader import CurlDownloaderAbstract, FileDownloaderFactory as ProductionFileDownloaderFactory
from downloader.local_repository import LocalRepository as ProductionLocalRepository
from downloader.target_path_repository import TargetPathRepository
from test.fake_importer_implicit_inputs import ImporterImplicitInputs
from test.fake_file_system_factory import FileSystemFactory
from test.fake_logger import NoLogger


class _TestDataCurlDownloader:
    def __init__(self, problematic_files, actual_description, missing_files):
        self._problematic_files = problematic_files
        self._actual_description = actual_description
        self._missing_files = missing_files

    def errors_at(self, file, tries=None):
        self._problematic_files[file] = tries if tries is not None else 99
        return self

    def brings_file(self, file, description):
        self._actual_description[file] = description
        return self

    def misses_file(self, file):
        self._missing_files.add(file)
        return self


class _FileDownloader(CurlDownloaderAbstract):
    def __init__(self, config, file_system, local_repository, problematic_files, actual_description, missing_files):
        self._file_system = file_system
        self._local_repository = local_repository
        super().__init__(config, self._file_system, self._local_repository, NoLogger(), True,
                         TargetPathRepository(config, self._file_system))
        self._problematic_files = problematic_files
        self._actual_description = actual_description
        self._missing_files = missing_files
        self._run_files = []

    def _run(self, description, target_path: str, file: str) -> None:
        self._run_files.append(file)

        if file in self._problematic_files:
            self._problematic_files[file] -= 1

        if file not in self._problematic_files or self._problematic_files[file] <= 0:
            if file in self._actual_description:
                description = self._actual_description[file]
            if file not in self._missing_files:
                if hasattr(self._file_system, 'test_data'):
                    self._file_system.test_data.with_file(target_path, description)
                else:
                    self._file_system.write_file_contents(target_path, 'This is a test file.')  # Generates a file with hash: test.objects.hash_real_test_file

            self._http_oks.add(file)
        else:
            self._errors.add_print_report(file, '')

    def _command(self, target_path: str, url: str) -> str:
        return target_path

    def _wait(self) -> None:
        pass

    def run_files(self) -> List[str]:
        return self._run_files


class FileDownloaderFactory(ProductionFileDownloaderFactory):
    def __init__(self, file_system_factory=None, local_repository=None, config=None, problematic_files=None, actual_description=None, missing_files=None):
        self.config = config if config is not None else default_config()
        self.file_system_factory = file_system_factory if file_system_factory is not None else FileSystemFactory(config=config)
        self._local_repository = local_repository
        self._problematic_files = dict() if problematic_files is None else problematic_files
        self._actual_description = dict() if actual_description is None else actual_description
        self._missing_files = set() if missing_files is None else missing_files

    def create(self, config, parallel_update, silent=False, hash_check=True):
        file_system = self.file_system_factory.create_for_config(config)
        local_repository = self._local_repository if self._local_repository is not None else ProductionLocalRepository(config, NoLogger(), file_system)
        return _FileDownloader(config, file_system, local_repository, self._problematic_files, self._actual_description, self._missing_files)

    @property
    def test_data(self) -> _TestDataCurlDownloader:
        return _TestDataCurlDownloader(self._problematic_files, self._actual_description, self._missing_files)

    @staticmethod
    def tester_from(implicit_inputs: ImporterImplicitInputs = None, file_downloader_factory=None, file_system_factory=None, local_repository=None, config=None):
        if implicit_inputs is not None:
            if file_system_factory is not None or file_downloader_factory is not None or local_repository is not None or config is not None:
                raise Exception('All others parameters must be None.')
            return FileDownloaderFactory.tester_from_implicit_inputs(implicit_inputs)

        if file_system_factory is not None and file_downloader_factory is not None:
            raise Exception('Either file_downloader_factory or file_system_factory must be None.')
        elif file_downloader_factory is None:
            return FileDownloaderFactory(config=config, file_system_factory=file_system_factory, local_repository=local_repository)
        else:
            return file_downloader_factory

    @staticmethod
    def tester_from_implicit_inputs(implicit_inputs):
        file_system_factory = FileSystemFactory(files=implicit_inputs.files, folders=implicit_inputs.folders,
                                                config=implicit_inputs.config, base_path=implicit_inputs.base_path,
                                                system_paths=implicit_inputs.system_paths)
        return FileDownloaderFactory(file_system_factory=file_system_factory, config=implicit_inputs.config,
                                     problematic_files=implicit_inputs.problematic_files,
                                     actual_description=implicit_inputs.actual_description,
                                     missing_files=implicit_inputs.missing_files)
