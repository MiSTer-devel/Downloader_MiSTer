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
from dataclasses import dataclass

from downloader.config import Config
from downloader.db_entity import DbEntity
from pathlib import Path

from downloader.job_system import Job
from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.copy_file_job import CopyFileJob
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.get_file_job import GetFileJob
from downloader.jobs.index import Index
from downloader.jobs.open_zip_contents_job import ZipKind
from downloader.jobs.open_zip_summary_job import OpenZipSummaryJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.validate_file_job import ValidateFileJob
from downloader.local_store_wrapper import StoreWrapper, new_store_fragment_drive_paths
from downloader.logger import Logger


@dataclass
class ZipJobContext:
    zip_id: str
    zip_description: Dict[str, Any]
    config: Config
    job: ProcessDbMainJob


def make_get_file_job(source: str, target: str, info: str, silent: bool, logger: Optional[Logger] = None) -> GetFileJob:
    if not source.startswith("http"):
        if logger: logger.debug('Loading db from fs: %s', source)
        return CopyFileJob(source=source, temp_path=target, info=info, silent=silent)
    else:
        if logger: logger.debug('Loading db from url: %s', source)
        return FetchFileJob(source=source, temp_path=target, info=info, silent=silent)


def make_get_data_job(source: str, description: dict[str, Any], logger: Optional[Logger] = None, /) -> FetchDataJob:
    if not source.startswith("http"):
        if logger: logger.debug('Loading db from fs: %s', source)
        return CopyDataJob(source, description)
    else:
        if logger: logger.debug('Loading db from url: %s', source)
        return FetchDataJob(source, description)


def get_data_job(description: Dict[str, Any], tag: Optional[str], /) -> FetchDataJob:
    job = make_get_data_job(description['url'], description)
    if tag is not None:
        job.add_tag(tag)
    return job

def make_get_zip_file_jobs(db: DbEntity, zip_id: str, description: Dict[str, Any], tag: Optional[str]) -> Tuple[GetFileJob, ValidateFileJob]:
    url = description['url']
    download_path = '/tmp/' + db.db_id.replace('/', '__') + '_._' + zip_id + '_._' + Path(url).name  # @TODO: Use proper tempfile.mkstemp instead
    info = f'temp zip file {db.db_id}:{zip_id}:{Path(url).name}'
    get_file_job = make_get_file_job(source=url, info=info, target=download_path, silent=True)
    validate_job = ValidateFileJob(temp_path=download_path, target_file_path=download_path, description=description, info=info, get_file_job=get_file_job)
    get_file_job.after_job = validate_job
    if tag is not None:
        get_file_job.add_tag(tag)
        validate_job.add_tag(tag)
    return get_file_job, validate_job


def make_open_zip_summary_job(z: ZipJobContext, file_description: Dict[str, Any], process_zip_backup: Optional[ProcessZipIndexJob]) -> Job:
    data_job = get_data_job(file_description, make_zip_tag(z.job.db, z.zip_id))
    open_zip_summary_job = OpenZipSummaryJob(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        full_resync=z.job.full_resync,
        transfer_job=data_job,
        config=z.config,
        backup=process_zip_backup
    )
    open_zip_summary_job.add_tag(make_zip_tag(z.job.db, z.zip_id))
    data_job.after_job = open_zip_summary_job
    if process_zip_backup is not None:
        process_zip_backup.summary_download_failed = data_job.source
    return data_job


def make_process_zip_job(zip_id: str, zip_description: Dict[str, Any], zip_summary: Dict[str, Any], config: Config, db: DbEntity, ini_description: Dict[str, Any], store: StoreWrapper, full_resync: bool, has_new_zip_summary: bool) -> ProcessZipIndexJob:
    base_files_url = db.base_files_url
    if 'base_files_url' in zip_description:
        base_files_url = zip_description['base_files_url']

    job = ProcessZipIndexJob(
        zip_id=zip_id,
        zip_description=zip_description,
        zip_index=Index(files=zip_summary['files'], folders=zip_summary['folders'], base_files_url=base_files_url),
        config=config,
        db=db,
        ini_description=ini_description,
        store=store,
        full_resync=full_resync,
        has_new_zip_summary=has_new_zip_summary,
        result_zip_index = new_store_fragment_drive_paths()
    )
    job.add_tag(make_zip_tag(db, zip_id))
    return job

def make_zip_tag(db: DbEntity, zip_id: str) -> str:  return f'{db.db_id}:zip:{zip_id}'

def make_zip_kind(kind: Optional[str], ctx: Any = None) -> Tuple[ZipKind, Optional[Exception]]:
    if kind == 'extract_all_contents':
        return ZipKind.EXTRACT_ALL_CONTENTS, None
    elif kind == 'extract_single_files':
        return ZipKind.EXTRACT_SINGLE_FILES, None
    else:
        return ZipKind.EXTRACT_SINGLE_FILES, Exception(f"Unknown kind '{kind}' for zip. '{ctx}'")
