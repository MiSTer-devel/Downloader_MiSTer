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

from dataclasses import dataclass
from typing import Optional

from downloader.config import Config, FileChecking
from downloader.db_utils import DbSectionPackage
from downloader.fail_policy import FailPolicy
from downloader.external_drives_repository import ExternalDrivesRepository
from downloader.file_system import FileSystem
from downloader.http_gateway import HttpGateway
from downloader.job_system import JobSystem, Worker, Job, JobContext, ProgressReporter
from downloader.jobs.check_mix_store_and_db_worker import CheckMixStoreAndDbWorker
from downloader.jobs.copy_data_job import CopyDataJob
from downloader.jobs.copy_data_worker import CopyDataWorker
from downloader.jobs.fetch_data_job import FetchDataJob
from downloader.jobs.fetch_data_worker import FetchDataWorker
from downloader.jobs.jobs_factory import make_transfer_job
from downloader.jobs.abort_worker import AbortWorker
from downloader.jobs.load_local_store_job import LoadLocalStoreJob, local_store_tag
from downloader.jobs.load_local_store_worker import LoadLocalStoreWorker
from downloader.jobs.load_local_store_fingerprints_job import LoadLocalStoreFingerprintsJob, local_store_fingerprints_tag
from downloader.jobs.load_local_store_fingerprints_worker import LoadLocalStoreFingerprintsWorker
from downloader.jobs.mix_store_and_db_job import MixStoreAndDbJob
from downloader.jobs.open_db_job import OpenDbJob
from downloader.jobs.open_db_worker import OpenDbWorker
from downloader.jobs.reporters import FileDownloadProgressReporter, InstallationReport, InstallationReportImpl
from downloader.jobs.worker_context import FailCtx
from downloader.local_repository import LocalRepository
from downloader.logger import Logger

STORE_FINGERPRINTS_LOAD_FAILED = 'store_fingerprints_load_failed'
STORE_LOAD_FAILED = 'store_load_failed'


@dataclass
class OnlineCheckerWorkers:
    workers: list[Worker]
    installation_report: InstallationReport


@dataclass
class OnlineCheckerJobs:
    jobs: list[Job]
    load_local_store_fingerprints_job: LoadLocalStoreFingerprintsJob
    load_local_store_job: LoadLocalStoreJob


class OnlineCheckerWorkersFactory:
    def __init__(
            self,
            worker_context: JobContext,
            progress_reporter: ProgressReporter,
            file_system: FileSystem,
            http_gateway: HttpGateway,
            logger: Logger,
            file_download_reporter: FileDownloadProgressReporter,
            local_repository: LocalRepository,
            config: Config,
            external_drives_repository: Optional[ExternalDrivesRepository] = None
    ):
        self._worker_context = worker_context
        self._progress_reporter = progress_reporter
        self._file_system = file_system
        self._http_gateway = http_gateway
        self._logger = logger
        self._file_download_reporter = file_download_reporter
        self._local_repository = local_repository
        self._config = config
        self._external_drives_repository = external_drives_repository

    def create_jobs(self, db_pkgs: list[DbSectionPackage]) -> OnlineCheckerJobs:
        jobs: list[Job] = []
        load_local_store_fingerprints_job = LoadLocalStoreFingerprintsJob()
        load_local_store_fingerprints_job.add_tag(local_store_fingerprints_tag)
        load_local_store_job = LoadLocalStoreJob(db_pkgs, self._config)
        load_local_store_job.add_tag(local_store_tag)
        for pkg in db_pkgs:
            transfer_job = make_transfer_job(pkg.section['db_url'], {}, True, pkg.db_id, priority=True)
            transfer_job.after_job = OpenDbJob(  # type: ignore[union-attr]
                transfer_job=transfer_job,
                section=pkg.db_id,
                ini_description=pkg.section,
                load_local_store_fingerprints_job=load_local_store_fingerprints_job,
                load_local_store_job=load_local_store_job,
            )
            jobs.append(transfer_job)  # type: ignore[arg-type]
        jobs.insert(int(len(jobs) / 2) + 1, load_local_store_fingerprints_job)
        return OnlineCheckerJobs(
            jobs=jobs,
            load_local_store_fingerprints_job=load_local_store_fingerprints_job,
            load_local_store_job=load_local_store_job,
        )

    def create_workers(self) -> OnlineCheckerWorkers:
        installation_report = InstallationReportImpl()
        self._file_download_reporter.set_installation_report(installation_report)

        checker_config = self._config.copy()
        checker_config['file_checking'] = FileChecking.FASTEST

        workers: list[Worker] = [
            AbortWorker(
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
            ),
            CopyDataWorker(
                file_system=self._file_system,
                progress_reporter=self._progress_reporter,
            ),
            FetchDataWorker(
                http_gateway=self._http_gateway,
                file_system=self._file_system,
                progress_reporter=self._progress_reporter,
                fail_ctx=FailCtx(self._logger, fail_policy=FailPolicy.FAULT_TOLERANT),
                timeout=self._config["downloader_timeout"],
            ),
            LoadLocalStoreFingerprintsWorker(
                logger=self._logger,
                local_repository=self._local_repository,
                progress_reporter=self._progress_reporter,
            ),
            LoadLocalStoreWorker(
                logger=self._logger,
                local_repository=self._local_repository,
                progress_reporter=self._progress_reporter,
                fail_ctx=FailCtx(self._logger, fail_policy=FailPolicy.FAULT_TOLERANT),
            ),
            OpenDbWorker(
                file_system=self._file_system,
                logger=self._logger,
                file_download_session_logger=self._file_download_reporter,
                installation_report=installation_report,
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
                fail_ctx=FailCtx(self._logger, fail_policy=FailPolicy.FAULT_TOLERANT),
                config=checker_config,
            ),
            CheckMixStoreAndDbWorker(
                logger=self._logger,
                installation_report=installation_report,
                worker_context=self._worker_context,
                progress_reporter=self._progress_reporter,
                external_drives_repository=self._external_drives_repository,
            ),
        ]
        return OnlineCheckerWorkers(workers=workers, installation_report=installation_report)


class OnlineChecker:
    def __init__(self, logger: Logger, job_system: JobSystem, worker_factory: OnlineCheckerWorkersFactory):
        self._logger = logger
        self._job_system = job_system
        self._worker_factory = worker_factory
        self._installation_report: InstallationReport = InstallationReportImpl()
        self._load_local_store_fingerprints_job: Optional[LoadLocalStoreFingerprintsJob] = None
        self._load_local_store_job: Optional[LoadLocalStoreJob] = None

    def _make_workers(self) -> dict[int, Worker]:
        workers = self._worker_factory.create_workers()
        self._installation_report = workers.installation_report
        return {w.job_type_id(): w for w in workers.workers}

    def _make_jobs(self, db_pkgs: list[DbSectionPackage]) -> list[Job]:
        jobs = self._worker_factory.create_jobs(db_pkgs)
        self._load_local_store_fingerprints_job = jobs.load_local_store_fingerprints_job
        self._load_local_store_job = jobs.load_local_store_job
        return jobs.jobs

    def check_dbs(self, db_pkgs: list[DbSectionPackage]) -> 'CheckBox':
        try:
            return self._check_dbs(db_pkgs)
        except Exception as error:
            self._logger.debug(error)
            check_box = CheckBox()
            check_box.set_error(error)
            self._logger.bench('OnlineChecker end.')
            return check_box

    def _check_dbs(self, db_pkgs: list[DbSectionPackage]) -> 'CheckBox':
        self._logger.bench('OnlineChecker start.')

        self._job_system.register_workers(self._make_workers())
        self._job_system.push_jobs(self._make_jobs(db_pkgs))

        self._logger.bench('OnlineChecker jobs begin.')
        self._job_system.execute_jobs()
        self._logger.bench('OnlineChecker jobs finished.')

        check_box = CheckBox()
        for _load_fingerprints_job, _e in self._installation_report.get_failed_jobs(LoadLocalStoreFingerprintsJob):
            check_box.add_fingerprint_failure(STORE_FINGERPRINTS_LOAD_FAILED)
        if self._load_local_store_job is not None \
                and len(self._installation_report.get_started_jobs(LoadLocalStoreJob)) > 0 \
                and self._load_local_store_job.local_store is None:
            check_box.add_fingerprint_failure(STORE_LOAD_FAILED)
        if len(check_box.fingerprint_failures()) > 0:
            self._logger.bench('OnlineChecker end.')
            return check_box

        db_states = {pkg.db_id: 0 for pkg in db_pkgs}
        for transfer_job, _e in self._installation_report.get_failed_jobs(FetchDataJob) + self._installation_report.get_failed_jobs(CopyDataJob):
            if transfer_job.db_id is not None:
                db_states[transfer_job.db_id] = 0
        for open_db_job in self._installation_report.get_completed_jobs(OpenDbJob):
            if open_db_job.skipped:
                db_states[open_db_job.section] = 1
        for mix_store_and_db_job in self._installation_report.get_completed_jobs(MixStoreAndDbJob):
            db_states[mix_store_and_db_job.db.db_id] = 1 if mix_store_and_db_job.skipped else 2

        for db_id, state in db_states.items():
            if state == 0:
                check_box.add_failed_db(db_id)
            elif state == 1:
                check_box.add_up_to_date_db(db_id)
            elif state == 2:
                check_box.add_need_update_db(db_id)

        self._logger.bench('OnlineChecker end.')
        return check_box

class CheckBox:
    def __init__(self) -> None:
        self._need_update_dbs: set[str] = set()
        self._failed_dbs: set[str] = set()
        self._up_to_date_dbs: set[str] = set()
        self._fingerprint_failures: set[str] = set()
        self._error: Optional[Exception] = None

    def add_need_update_db(self, db_id: str) -> None:
        self._need_update_dbs.add(db_id)

    def add_failed_db(self, db_id: str) -> None:
        self._failed_dbs.add(db_id)

    def add_up_to_date_db(self, db_id: str) -> None:
        self._up_to_date_dbs.add(db_id)

    def add_fingerprint_failure(self, failure_id: str) -> None:
        self._fingerprint_failures.add(failure_id)

    def set_error(self, error: Exception) -> None:
        self._error = error

    def need_update_dbs(self) -> list[str]: return list(self._need_update_dbs)
    def failed_dbs(self) -> list[str]: return list(self._failed_dbs)
    def up_to_date_dbs(self) -> list[str]: return list(self._up_to_date_dbs)
    def fingerprint_failures(self) -> list[str]: return list(self._fingerprint_failures)
    def error(self) -> Optional[Exception]: return self._error
