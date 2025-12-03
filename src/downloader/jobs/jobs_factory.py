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


from typing import Optional, Any
from dataclasses import dataclass

from downloader.config import Config, ConfigDatabaseSection
from downloader.db_entity import DbEntity, ZipIndexEntity

from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.open_zip_contents_job import ZipKind
from downloader.jobs.open_zip_summary_job import OpenZipSummaryJob
from downloader.jobs.process_db_main_job import ProcessDbMainJob
from downloader.jobs.process_zip_index_job import ProcessZipIndexJob
from downloader.jobs.transfer_job import TransferJob
from downloader.local_store_wrapper import new_store_fragment_drive_paths, ReadOnlyStoreAdapter


def make_transfer_job(source: str, description: dict[str, Any], do_calcs: bool, db_id: Optional[str], /) -> TransferJob:
    job: TransferJob
    if not source.startswith("http"):
        job = CopyDataJob(source, description, {} if do_calcs else None, db_id)
    else:
        job = FetchDataJob(source, description, {} if do_calcs else None, db_id)
    return job

@dataclass
class ZipJobContext:
    zip_id: str
    zip_description: dict[str, Any]
    config: Config
    job: ProcessDbMainJob

def make_open_zip_summary_job(z: ZipJobContext, file_description: dict[str, Any], process_zip_backup: Optional[ProcessZipIndexJob]) -> TransferJob:
    zip_tag = make_zip_tag(z.job.db, z.zip_id)
    transfer_job = make_transfer_job(file_description['url'], file_description, False, z.job.db.db_id)
    transfer_job.add_tag(zip_tag)  # type: ignore[union-attr]
    open_zip_summary_job = OpenZipSummaryJob(
        zip_id=z.zip_id,
        zip_description=z.zip_description,
        db=z.job.db,
        ini_description=z.job.ini_description,
        store=z.job.store,
        transfer_job=transfer_job,
        config=z.config,
        backup=process_zip_backup
    )
    open_zip_summary_job.add_tag(zip_tag)
    transfer_job.after_job = open_zip_summary_job   # type: ignore[union-attr]
    if process_zip_backup is not None:
        process_zip_backup.summary_download_failed = transfer_job.source   # type: ignore[union-attr]
    return transfer_job


def make_process_zip_index_job(zip_id: str, zip_index: ZipIndexEntity, config: Config, db: DbEntity, ini_description: ConfigDatabaseSection, store: ReadOnlyStoreAdapter, has_new_zip_summary: bool) -> ProcessZipIndexJob:
    job = ProcessZipIndexJob(
        zip_id=zip_id,
        zip_index=zip_index,
        config=config,
        db=db,
        ini_description=ini_description,
        store=store,
        has_new_zip_summary=has_new_zip_summary,
        result_zip_index = new_store_fragment_drive_paths()
    )
    job.add_tag(make_zip_tag(db, zip_id))
    return job

def make_zip_tag(db: DbEntity, zip_id: str) -> str:  return f'{db.db_id}:zip:{zip_id}'

def make_zip_kind(kind: Optional[str], ctx: Any = None) -> tuple[ZipKind, Optional[Exception]]:
    if kind == 'extract_all_contents':
        return ZipKind.EXTRACT_ALL_CONTENTS, None
    elif kind == 'extract_single_files':
        return ZipKind.EXTRACT_SINGLE_FILES, None
    else:
        return ZipKind.EXTRACT_SINGLE_FILES, Exception(f"Unknown kind '{kind}' for zip. '{ctx}'")
