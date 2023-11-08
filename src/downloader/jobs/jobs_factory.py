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


from typing import Optional, Dict, Any, Tuple

from downloader.db_entity import DbEntity
from pathlib import Path
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.get_file_job import GetFileJob
from downloader.jobs.index import Index
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.local_store_wrapper import StoreWrapper
from downloader.logger import Logger


def make_get_file_job(source: str, target: str, info: str, silent: bool, logger: Optional[Logger] = None) -> GetFileJob:
    if not source.startswith("http"):
        if logger: logger.debug(f'Loading db from fs: {source}')
        return CopyFileJob(source=source, temp_path=target, info=info, silent=silent)
    else:
        if logger: logger.debug(f'Loading db from url: {source}')
        return FetchFileJob2(source=source, temp_path=target, info=info, silent=silent)


def make_get_zip_file_jobs(db: DbEntity, zip_id: str, description: Dict[str, Any]) -> Tuple[GetFileJob, ValidateFileJob2]:
    url = description['url']
    download_path = '/tmp/' + db.db_id + '_._' + zip_id + '_._' + Path(url).name
    get_file_job = make_get_file_job(source=url, info=zip_id, target=download_path, silent=False)
    validate_job = ValidateFileJob2(temp_path=download_path, target_file_path=download_path, description=description, info=zip_id, get_file_job=get_file_job)
    get_file_job.after_job = validate_job
    return get_file_job, validate_job


def make_process_zip_job(zip_id: str, zip_description: Dict[str, Any], zip_index: Dict[str, Any], config: Dict[str, Any], db: DbEntity, ini_description: Dict[str, Any], store: StoreWrapper, full_resync: bool, has_new_zip_index: bool) -> ProcessZipJob:
    base_files_url = db.base_files_url
    if 'base_files_url' in zip_description:
        base_files_url = zip_description['base_files_url']

    return ProcessZipJob(
        zip_id=zip_id,
        zip_description=zip_description,
        zip_index=Index(files=zip_index['files'], folders=zip_index['folders'], base_files_url=base_files_url),
        config=config,
        db=db,
        ini_description=ini_description,
        store=store,
        full_resync=full_resync,
        has_new_zip_index=has_new_zip_index
    )