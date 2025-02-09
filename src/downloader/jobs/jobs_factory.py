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


from typing import Callable, Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

from downloader.config import Config
from downloader.db_entity import DbEntity
from pathlib import Path

from downloader.file_filter import FileFoldersHolder
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.get_file_job import GetFileJob
from downloader.jobs.index import Index
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.jobs.process_index_job import ProcessIndexJob
from downloader.path_package import PathPackage
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.local_store_wrapper import StoreWrapper, new_store_fragment_drive_paths
from downloader.logger import Logger


@dataclass
class ZipJobContext:
    zip_id: str
    zip_description: Dict[str, Any]
    config: Config
    job: ProcessDbJob


def make_get_file_job(source: str, target: str, info: str, silent: bool, logger: Optional[Logger] = None) -> GetFileJob:
    if not source.startswith("http"):
        if logger: logger.debug(f'Loading db from fs: {source}')
        return CopyFileJob(source=source, temp_path=target, info=info, silent=silent)
    else:
        if logger: logger.debug(f'Loading db from url: {source}')
        return FetchFileJob(source=source, temp_path=target, info=info, silent=silent)


def make_get_zip_file_jobs(db: DbEntity, zip_id: str, description: Dict[str, Any]) -> Tuple[GetFileJob, ValidateFileJob, str]:
    url = description['url']
    download_path = '/tmp/' + db.db_id + '_._' + zip_id + '_._' + Path(url).name
    info = f'temp zip file {db.db_id}:{zip_id}:{Path(url).name}'
    get_file_job = make_get_file_job(source=url, info=info, target=download_path, silent=False)
    get_file_job.add_tag(make_zip_tag(db, zip_id))
    validate_job = ValidateFileJob(temp_path=download_path, target_file_path=download_path, description=description, info=info, get_file_job=get_file_job)
    validate_job.add_tag(make_zip_tag(db, zip_id))
    get_file_job.after_job = validate_job
    return get_file_job, validate_job, info


def make_open_zip_index_job(z: ZipJobContext, file_description: Dict[str, Any], process_zip_backup: Optional[ProcessZipJob]) -> Tuple[GetFileJob, str]:
    get_file_job, validate_job, info = make_get_zip_file_jobs(db=z.job.db, zip_id=z.zip_id, description=file_description)
    open_zip_index_job = OpenZipIndexJob(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        full_resync=z.job.full_resync,
        download_path=validate_job.target_file_path,
        config=z.config,
        get_file_job=get_file_job,
        process_zip_backup=process_zip_backup
    )
    open_zip_index_job.add_tag(make_zip_tag(z.job.db, z.zip_id))
    validate_job.after_job = open_zip_index_job
    if process_zip_backup is not None:
        process_zip_backup.summary_download_failed = validate_job.info
    return get_file_job, info


def make_open_zip_contents_job(job: ProcessZipJob, zip_index: Index, file_packs: List[PathPackage], folder_packs: List[PathPackage], filtered_data: FileFoldersHolder, make_process_index_backup: Callable[[], ProcessIndexJob]) -> Tuple[GetFileJob, str]:
    get_file_job, validate_job, info = make_get_zip_file_jobs(db=job.db, zip_id=job.zip_id, description=job.zip_description['contents_file'])
    open_zip_contents_job = OpenZipContentsJob(
        zip_id=job.zip_id,
        zip_description=job.zip_description,
        db=job.db,
        ini_description=job.ini_description,
        store=job.store,
        full_resync=job.full_resync,
        download_path=validate_job.target_file_path,
        files=file_packs,
        folders=folder_packs,
        config=job.config,
        index=zip_index,
        get_file_job=get_file_job,
        filtered_data=filtered_data,
        make_process_index_backup=make_process_index_backup
    )
    open_zip_contents_job.add_tag(make_zip_tag(job.db, job.zip_id))
    validate_job.after_job = open_zip_contents_job
    return get_file_job, info


def make_process_zip_job(zip_id: str, zip_description: Dict[str, Any], zip_index: Dict[str, Any], config: Config, db: DbEntity, ini_description: Dict[str, Any], store: StoreWrapper, full_resync: bool, has_new_zip_index: bool) -> ProcessZipJob:
    base_files_url = db.base_files_url
    if 'base_files_url' in zip_description:
        base_files_url = zip_description['base_files_url']

    job = ProcessZipJob(
        zip_id=zip_id,
        zip_description=zip_description,
        zip_index=Index(files=zip_index['files'], folders=zip_index['folders'], base_files_url=base_files_url),
        config=config,
        db=db,
        ini_description=ini_description,
        store=store,
        full_resync=full_resync,
        has_new_zip_index=has_new_zip_index,
        result_zip_index = new_store_fragment_drive_paths()
    )
    job.add_tag(make_zip_tag(db, zip_id))
    return job

def make_zip_tag(db: DbEntity, zip_id: str) -> str:  return f'{db.db_id}:{zip_id}'
