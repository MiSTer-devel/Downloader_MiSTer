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

from typing import TypedDict

from downloader.db_utils import DbSectionPackage
from downloader.job_system import JobSystem, Worker, Job
from downloader.jobs.check_db_job import CheckDbJob
from downloader.jobs.jobs_factory import make_transfer_job
from downloader.jobs.load_local_store_sigs_job import LoadLocalStoreSigsJob, local_store_sigs_tag
from downloader.jobs.reporters import InstallationReport
from downloader.online_importer_workers_factory import OnlineImporterWorkersFactory
from downloader.logger import Logger


class OnlineChecker:
    def __init__(self, logger: Logger, job_system: JobSystem, worker_factory: OnlineImporterWorkersFactory, installation_report: InstallationReport):
        self._logger = logger
        self._job_system = job_system
        self._worker_factory = worker_factory
        self._installation_report = installation_report

    def _make_workers(self) -> dict[int, Worker]:
        return {w.job_type_id(): w for w in self._worker_factory.create_workers()}

    def _make_jobs(self, db_pkgs: list[DbSectionPackage]) -> list[Job]:
        jobs: list[Job] = []
        load_local_store_sigs_job = LoadLocalStoreSigsJob()
        load_local_store_sigs_job.add_tag(local_store_sigs_tag)
        for pkg in db_pkgs:
            transfer_job = make_transfer_job(pkg.section['db_url'], {}, True, pkg.db_id)
            transfer_job.after_job = CheckDbJob(
                transfer_job=transfer_job,
                section=pkg.db_id,
                ini_description=pkg.section,
                load_local_store_sigs_job=load_local_store_sigs_job,
            )
            jobs.append(transfer_job)  # type: ignore[arg-type]
        jobs.insert(int(len(jobs) / 2) + 1, load_local_store_sigs_job)
        return jobs

    def check_dbs(self, db_pkgs: list[DbSectionPackage]) -> 'CheckBox':
        self._logger.bench('OnlineChecker start.')

        self._job_system.register_workers(self._make_workers())
        self._job_system.push_jobs(self._make_jobs(db_pkgs))

        self._logger.bench('OnlineChecker jobs begin.')
        self._job_system.execute_jobs()
        self._logger.bench('OnlineChecker jobs finished.')

        db_states = {pkg.db_id: 0 for pkg in db_pkgs}
        for check_db_job in self._installation_report.get_completed_jobs(CheckDbJob):
            db_states[check_db_job.section] = 1 if check_db_job.skipped else 2

        check_box: CheckBox = {
            'failed_db_ids': [db_id for db_id, state in db_states.items() if state == 0],
            'up_to_date_db_ids': [db_id for db_id, state in db_states.items() if state == 1],
            'need_update_db_ids': [db_id for db_id, state in db_states.items() if state == 2],
        }

        self._logger.bench('OnlineChecker end.')
        return check_box

class CheckBox(TypedDict):
    need_update_db_ids: list[str]
    failed_db_ids: list[str]
    up_to_date_db_ids: list[str]
