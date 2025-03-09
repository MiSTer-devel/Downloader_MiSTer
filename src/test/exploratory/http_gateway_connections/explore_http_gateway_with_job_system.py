#!/usr/bin/env python3
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

import os
import signal
import ssl
import time
import sys
from pathlib import Path
from typing import List, Tuple

from downloader.config import default_config
from downloader.file_system import FileSystemFactory
from downloader.job_system import JobSystem, ProgressReporter, Job
from downloader.jobs.fetch_file_job import FetchFileJob
from downloader.jobs.fetch_file_worker import FetchFileWorker
from downloader.jobs.jobs_factory import make_persistent_transfer_job
from downloader.logger import PrintLogger, Logger
from downloader.http_gateway import HttpGateway
from downloader.path_package import PathPackage, PATH_TYPE_FILE, PATH_PACKAGE_KIND_STANDARD
from test.exploratory.http_gateway_connections.explore_http_gateway_with_real_urls import urls
from test.fake_logger import DescribeNowDecorator


def main() -> None:
    logger = DescribeNowDecorator(PrintLogger())
    with HttpGateway(ssl_ctx=ssl.create_default_context(), timeout=180, logger=logger) as gw:

        fs = FileSystemFactory(default_config(), {}, logger=logger)
        reporter = Reporter(fs, gw, logger=logger)
        job_system = JobSystem(reporter=reporter, logger=logger, max_threads=20)
        job_system.set_interfering_signals([signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT])

        job_system.register_worker(FetchFileJob.type_id, FetchFileWorker(
            progress_reporter=reporter, file_system=fs.create_for_system_scope(), http_gateway=gw, timeout=600
        ))

        dir_path = f'{os.path.dirname(os.path.realpath(__file__))}/delme'
        os.makedirs(dir_path, exist_ok=True)

        for i in range(20):
            for u in urls:
                fetch = make_persistent_transfer_job(
                    u,
                    True,
                    PathPackage(
                        f'{i}_{Path(u).name}_{len(u)}',
                        dir_path,
                        {'tmp': f'{i}_{Path(u).name[-30:]}_{len(u)}'},
                        PATH_TYPE_FILE,
                        PATH_PACKAGE_KIND_STANDARD,
                        None
                    ),
                    None
                )
                job_system.push_job(fetch)

        start = time.time()
        job_system.execute_jobs()
        end = time.time()

    print()
    print('Completed jobs: ')
    for completed in reporter.completed:
        print(completed.info)

    print()
    print('Failed jobs: ')
    for failed, e in reporter.failed:
        print(failed, e)

    print()
    print('Completed jobs: ' + str(len(reporter.completed)))
    print('Failed jobs: ' + str(len(reporter.failed)))
    print('Cancelled jobs: ' + str(len(reporter.cancelled)))
    print()
    print(f'Time: {end - start}s')
    if reporter.cancelled: sys.exit(1)

class Reporter(ProgressReporter):
    def __init__(self, fs: FileSystemFactory, gw: HttpGateway, logger: Logger):
        self._fs = fs
        self._gw = gw
        self._logger = logger
        self._cancelled = False

    def notify_work_in_progress(self) -> None: pass
    def notify_job_retried(self, job: Job, retry_job: Job, exception: Exception) -> None: pass
    def notify_job_started(self, job: Job) -> None: pass

    completed: List[FetchFileJob] = []
    failed: List[Tuple[FetchFileJob, Exception]] = []
    cancelled: List[FetchFileJob] = []

    def notify_job_completed(self, job: FetchFileJob, next_jobs: List[Job]) -> None:  # type: ignore[override]
        self._logger.print(f'>>>>>> COMPLETED! {job.info}')
        self.completed.append(job)

    def notify_job_failed(self, job: FetchFileJob, exception: Exception) -> None:  # type: ignore[override]
        self._logger.print(f'>>>>>> FAILED! {job.info}', exception)
        self.failed.append((job, exception))

    def notify_jobs_cancelled(self, jobs: List[FetchFileJob]) -> None:  # type: ignore[override]
        self.cancelled.extend(jobs)

        if self._cancelled: return
        self._logger.print(f">>>>>> CANCELING PENDING JOBS!")
        self._fs.cancel_ongoing_operations()
        self._gw.cleanup()
        self._cancelled = True

if __name__ == '__main__':
    main()
