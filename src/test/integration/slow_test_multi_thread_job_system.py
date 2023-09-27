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

from downloader.job_system import JobSystem, ProgressReporter
from typing import Dict, Optional

from downloader.logger import NoLogger
from test.unit.test_single_thread_job_system import TestSingleThreadJobSystem


class TestMultiThreadJobSystem(TestSingleThreadJobSystem):

    def test_base_provides_tests(self): self.assertGreater(len([m for m in dir(self) if m.startswith('test_')]), 5)
    def sut(self, reporter: ProgressReporter) -> JobSystem: return JobSystem(reporter, logger=NoLogger(), max_threads=20)

    def assertReports(self, completed: Optional[Dict[int, int]] = None, started: Optional[Dict[int, int]] = None, in_progress: Optional[Dict[int, int]] = None, failed: Optional[Dict[int, int]] = None, retried: Optional[Dict[int, int]] = None, pending: int = 0):
        self.assertEqual({
            'completed_jobs': completed or {},
            'started_jobs': started or completed or {},
            'in_progress_jobs': in_progress or {},
            'failed_jobs': failed or {},
            'retried_jobs': retried or {},
            'pending_jobs_amount': pending
        }, {
            'completed_jobs': self.reporter.completed_jobs,
            'started_jobs': self.reporter.started_jobs,
            'in_progress_jobs': self.reporter.in_progress_jobs,
            'failed_jobs': self.reporter.failed_jobs,
            'retried_jobs': self.reporter.retried_jobs,
            'pending_jobs_amount': self.system.pending_jobs_amount()
        })
