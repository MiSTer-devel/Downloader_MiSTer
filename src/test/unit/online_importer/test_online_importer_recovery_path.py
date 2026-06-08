# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

import unittest

from downloader.constants import DISTRIBUTION_MISTER_DB_ID, EXIT_ERROR_BAD_NEW_BINARY, FILE_MiSTer, FILE_MiSTer_old, \
    MEDIA_USB0, SUFFIX_file_in_progress
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.open_zip_contents_job import OpenZipContentsJob, ZipKind
from downloader.path_package import PATH_PACKAGE_KIND_STANDARD, PATH_TYPE_FILE, PathPackage
from test.fake_file_system_factory import fs_records
from test.fake_importer_implicit_inputs import FileSystemState
from test.fake_online_importer import OnlineImporter
from test.objects import config_with, db_entity, db_test, empty_test_store, file_a, file_descr, file_mister_descr, \
    hash_MiSTer_old, media_usb0


class TestOnlineImporterRecoveryPath(unittest.TestCase):
    """
    Specification for the post-download MiSTer binary recovery gate.

    The recovery path is intentionally narrow: it should only run for a failed MiSTer
    binary update when the target existed before the attempted update. These tests use
    a pre-built installation report so they exercise the importer recovery decision
    directly while keeping all file operations on the fake filesystem.
    """

    def test_failed_existing_mister_update___with_backup_and_missing_target___restores_backup(self):
        job = self.failed_fetch_job(FILE_MiSTer, file_mister_descr(), already_exists=True, db_id=DISTRIBUTION_MISTER_DB_ID)
        sut = self.online_importer_with_failed_job(job, files={
            media_usb0(FILE_MiSTer_old): {'hash': hash_MiSTer_old},
        })

        box, _error = sut.download_dbs_contents([])

        self.assertTrue(sut.file_system.is_file(media_usb0(FILE_MiSTer), use_cache=False))
        self.assertFalse(sut.file_system.is_file(media_usb0(FILE_MiSTer_old), use_cache=False))
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (media_usb0(FILE_MiSTer_old), media_usb0(FILE_MiSTer))},
        ]), sut.file_system.write_records)
        self.assertEqual([FILE_MiSTer], box.failed_files())

    def test_failed_existing_non_mister_update___with_missing_target___does_not_run_mister_recovery(self):
        job = self.failed_fetch_job(file_a, file_descr(), already_exists=True, db_id=db_test)
        sut = self.online_importer_with_failed_job(job)

        box, _error = sut.download_dbs_contents([])

        self.assertFalse(sut.file_system.is_file(media_usb0(file_a), use_cache=False))
        self.assertEqual([], sut.file_system.write_records)
        self.assertEqual([file_a], box.failed_files())

    def test_failed_existing_file_without_backup_or_tmp___with_valid_in_progress_file___does_not_restore(self):
        description = file_descr()
        job = self.failed_fetch_job(file_a, description, already_exists=True, db_id=db_test)
        sut = self.online_importer_with_failed_job(job, files={
            media_usb0(file_a + SUFFIX_file_in_progress): {'hash': description['hash']},
        })

        box, _error = sut.download_dbs_contents([])

        self.assertFalse(sut.file_system.is_file(media_usb0(file_a), use_cache=False))
        self.assertTrue(sut.file_system.is_file(media_usb0(file_a + SUFFIX_file_in_progress), use_cache=False))
        self.assertEqual([], sut.file_system.write_records)
        self.assertEqual([file_a], box.failed_files())

    def test_failed_existing_non_mister_with_backup___when_recovery_cannot_restore___does_not_exit(self):
        description = {**file_descr(), 'backup': file_a + '.old'}
        job = self.failed_fetch_job(file_a, description, already_exists=True, db_id=db_test)
        sut = self.online_importer_with_failed_job(job)

        box, _error = sut.download_dbs_contents([])

        self.assertFalse(sut.file_system.is_file(media_usb0(file_a), use_cache=False))
        self.assertFalse(sut.file_system.is_file(media_usb0(description['backup']), use_cache=False))
        self.assertEqual([], sut.file_system.write_records)
        self.assertEqual([file_a], box.failed_files())

    def test_failed_fresh_mister_install___with_backup_and_missing_target___does_not_run_mister_recovery(self):
        job = self.failed_fetch_job(FILE_MiSTer, file_mister_descr(), already_exists=False, db_id=DISTRIBUTION_MISTER_DB_ID)
        sut = self.online_importer_with_failed_job(job, files={
            media_usb0(FILE_MiSTer_old): {'hash': hash_MiSTer_old},
        })

        box, _error = sut.download_dbs_contents([])

        self.assertFalse(sut.file_system.is_file(media_usb0(FILE_MiSTer), use_cache=False))
        self.assertTrue(sut.file_system.is_file(media_usb0(FILE_MiSTer_old), use_cache=False))
        self.assertEqual([], sut.file_system.write_records)
        self.assertEqual([FILE_MiSTer], box.failed_files())

    def test_zip_unrecoverable_file___with_backup_and_missing_target___restores_backup(self):
        description = {**file_descr(), 'backup': file_a + '.old'}
        zip_job = self.completed_open_zip_job_with_failed_file(self.pkg(file_a, description))
        sut = self.online_importer_with_completed_job(zip_job, files={
            media_usb0(description['backup']): {'hash': 'old-a'},
        })

        box = sut.add_db(db_entity(db_id=db_test), empty_test_store()).download().box()

        self.assertTrue(sut.file_system.is_file(media_usb0(file_a), use_cache=False))
        self.assertFalse(sut.file_system.is_file(media_usb0(description['backup']), use_cache=False))
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (media_usb0(description['backup']), media_usb0(file_a))},
        ]), sut.file_system.write_records)
        self.assertEqual([file_a], box.failed_files())

    def test_zip_unrecoverable_file___with_valid_tmp_and_missing_target___restores_tmp(self):
        description = {**file_descr(), 'tmp': file_a + '.tmp'}
        zip_job = self.completed_open_zip_job_with_failed_file(self.pkg(file_a, description))
        sut = self.online_importer_with_completed_job(zip_job, files={
            media_usb0(description['tmp']): {'hash': description['hash']},
        })

        box = sut.add_db(db_entity(db_id=db_test), empty_test_store()).download().box()

        self.assertTrue(sut.file_system.is_file(media_usb0(file_a), use_cache=False))
        self.assertFalse(sut.file_system.is_file(media_usb0(description['tmp']), use_cache=False))
        self.assertEqual(fs_records([
            {'scope': 'move', 'data': (media_usb0(description['tmp']), media_usb0(file_a))},
        ]), sut.file_system.write_records)
        self.assertEqual([file_a], box.failed_files())

    def test_zip_unrecoverable_mister___when_recovery_cannot_restore___exits(self):
        zip_job = self.completed_open_zip_job_with_failed_file(self.pkg(FILE_MiSTer, file_mister_descr()))
        sut = self.online_importer_with_completed_job(zip_job)

        with self.assertRaises(SystemExit) as cm:
            sut.add_db(db_entity(db_id=DISTRIBUTION_MISTER_DB_ID), empty_test_store()).download()

        self.assertEqual(EXIT_ERROR_BAD_NEW_BINARY, cm.exception.code)

    def online_importer_with_failed_job(self, job, files=None):
        job_system = FailedFetchJobSystem(job)
        sut = OnlineImporter(file_system_state=FileSystemState(files=files), job_system=job_system)
        job_system.reporter = sut._file_download_reporter
        return sut

    def online_importer_with_completed_job(self, job, files=None):
        job_system = CompletedJobSystem(job)
        sut = OnlineImporter(file_system_state=FileSystemState(files=files), job_system=job_system)
        job_system.reporter = sut._file_download_reporter
        return sut

    def failed_fetch_job(self, rel_path, description, already_exists, db_id):
        return FetchFileJob(
            description['url'],
            already_exists,
            self.pkg(rel_path, description),
            db_id
        )

    def completed_open_zip_job_with_failed_file(self, pkg):
        job = OpenZipContentsJob(
            db=db_entity(db_id=db_test),
            store=None,
            ini_description={},
            config=config_with(),
            zip_id='zip',
            zip_kind=ZipKind.EXTRACT_SINGLE_FILES,
            zip_description={},
            target_folder=None,
            total_amount_of_files_in_zip=1,
            files_to_unzip=[pkg],
            recipient_folders=[],
            transfer_job=None,
            action_text='',
            zip_base_files_url='',
            filtered_data={'files': {}, 'folders': {}}
        )
        job.failed_files.append(pkg)
        return job

    def pkg(self, rel_path, description):
        return PathPackage(rel_path, MEDIA_USB0, description, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD, None)


class FailedFetchJobSystem:
    def __init__(self, job):
        self.job = job
        self.reporter = None

    def register_workers(self, _workers):
        pass

    def push_jobs(self, _jobs):
        pass

    def pending_jobs_amount(self):
        return 0

    def execute_jobs(self):
        self.reporter.notify_job_started(self.job)
        self.reporter.notify_job_failed(self.job, Exception('forced fetch failure'))


class CompletedJobSystem:
    def __init__(self, job):
        self.job = job
        self.reporter = None

    def register_workers(self, _workers):
        pass

    def push_jobs(self, _jobs):
        pass

    def pending_jobs_amount(self):
        return 0

    def execute_jobs(self):
        self.reporter.notify_job_started(self.job)
        self.reporter.notify_job_completed(self.job, [])
