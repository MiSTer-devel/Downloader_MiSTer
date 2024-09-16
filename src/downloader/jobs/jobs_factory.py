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


from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass

from downloader.db_entity import DbEntity
from pathlib import Path
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_file_job2 import FetchFileJob2
from downloader.jobs.get_file_job import GetFileJob
from downloader.jobs.index import Index
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob
from downloader.jobs.open_zip_index_job import OpenZipIndexJob
from downloader.jobs.path_package import PathPackage
from downloader.jobs.process_db_job import ProcessDbJob
from downloader.jobs.process_zip_job import ProcessZipJob
from downloader.jobs.validate_file_job2 import ValidateFileJob2
from downloader.local_store_wrapper import StoreWrapper
from downloader.logger import Logger


@dataclass
class ZipJobContext:
    zip_id: str
    zip_description: Dict[str, Any]
    config: Dict[str, Any]
    job: ProcessDbJob


def make_get_file_job(source: str, target: str, info: str, silent: bool, logger: Optional[Logger] = None) -> GetFileJob:
    if not source.startswith("http"):
        if logger: logger.debug(f'Loading db from fs: {source}')
        return CopyFileJob(source=source, temp_path=target, info=info, silent=silent)
    else:
        if logger: logger.debug(f'Loading db from url: {source}')
        return FetchFileJob2(source=source, temp_path=target, info=info, silent=silent)


def make_get_zip_file_jobs(db: DbEntity, zip_id: str, description: Dict[str, Any], zip_tag: str) -> Tuple[GetFileJob, ValidateFileJob2, str]:
    url = description['url']
    download_path = '/tmp/' + db.db_id + '_._' + zip_id + '_._' + Path(url).name
    info = f'temp zip file {db.db_id}:{zip_id}:{Path(url).name}'
    get_file_job = make_get_file_job(source=url, info=info, target=download_path, silent=False)
    get_file_job.add_tag(zip_tag)
    validate_job = ValidateFileJob2(temp_path=download_path, target_file_path=download_path, description=description, info=info, get_file_job=get_file_job)
    validate_job.add_tag(zip_tag)
    get_file_job.after_job = validate_job
    return get_file_job, validate_job, info


def make_open_zip_index_job(z: ZipJobContext, file_description: Dict[str, Any]) -> Tuple[GetFileJob, str]:
    zip_tag = f'{z.job.db.db_id}:{z.zip_id}'
    get_file_job, validate_job, info = make_get_zip_file_jobs(db=z.job.db, zip_id=z.zip_id, description=file_description, zip_tag=zip_tag)
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
    )
    open_zip_index_job.add_tag(zip_tag)
    validate_job.after_job = open_zip_index_job
    return get_file_job, info


def make_open_zip_contents_job(job: ProcessZipJob, file_packs: List[PathPackage]) -> Tuple[GetFileJob, str]:
    zip_tag = f'{job.db.db_id}:{job.zip_id}'
    get_file_job, validate_job, info = make_get_zip_file_jobs(db=job.db, zip_id=job.zip_id, description=job.zip_description['contents_file'], zip_tag=zip_tag)
    open_zip_contents_job = OpenZipContentsJob(
        zip_id=job.zip_id,
        zip_description=job.zip_description,
        db=job.db,
        ini_description=job.ini_description,
        store=job.store,
        full_resync=job.full_resync,
        download_path=validate_job.target_file_path,
        files=file_packs,
        config=job.config,
        index=job.zip_index,
        get_file_job=get_file_job
    )
    open_zip_contents_job.add_tag(zip_tag)
    validate_job.after_job = open_zip_contents_job
    return get_file_job, info


def make_process_zip_job(zip_id: str, zip_description: Dict[str, Any], zip_index: Dict[str, Any], config: Dict[str, Any], db: DbEntity, ini_description: Dict[str, Any], store: StoreWrapper, full_resync: bool, has_new_zip_index: bool) -> ProcessZipJob:
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
        has_new_zip_index=has_new_zip_index
    )
    job.add_tag(f'{db.db_id}:{zip_id}')

    return job
