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

from typing import List, Union
import unittest

from downloader.job_system import Job
from downloader.jobs.reporters import InstallationReportImpl

class TestInstallationReportImpl(unittest.TestCase):

    def setUp(self):
        self.report = InstallationReportImpl()
        self.job_a = job('a')
        self.job_b = job('b')
        self.e = Exception('No reason')

    def test_any_in_progress_job_with_tag_a___after_start_job_with_tag_a___returns_true_and_viceversa(self):
        self.report.add_job_started(self.job_a)
        for valid_tags in (['a'], ['b', 'a'], ['a', 'b']):
            with self.subTest(tags=valid_tags):
                self.assertTrue(self.report.any_in_progress_job_with_tags(valid_tags))
        for wrong_tags in (['b'], ['b', 'c'], ['c', 'b']):
            with self.subTest(tags=wrong_tags):
                self.assertFalse(self.report.any_in_progress_job_with_tags(wrong_tags))

    def test_tags_a_b___after_start_job_with_two_tags_a_b_in_it___returns_true_for_both_tags_separately_and_combined(self):
        self.report.add_job_started(job(['a', 'b']))
        self.assertTrue(self.tags(['a']))
        self.assertTrue(self.tags(['b']))
        self.assertTrue(self.tags(['a', 'b']))

    def test_tag_a___after_start_and_complete_job_a___returns_false(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_completed(self.job_a, [])
        self.assertFalse(self.tags(['a']))
    
    def test_tag_a___after_start_job_a_and_complete_another_job_a___return_true_because_they_have_different_identity(self):
        self.report.add_job_started(job('a'))
        self.report.add_job_completed(job('a'), [])
        self.assertTrue(self.tags(['a']))

    def test_tag_a___after_fail_job_a_and_then_start_job_a___returns_false_because_we_have_eventual_consistency(self):
        self.report.add_job_failed(self.job_a, self.e)
        self.report.add_job_started(self.job_a)
        self.assertFalse(self.tags(['a']))

    def test_tag_a___after_complete_job_a_with_a_child___returns_true_because_the_child_is_inmediately_active(self):
        self.report.add_job_completed(self.job_a, [job('a')])
        self.assertTrue(self.tags(['a']))

    def test_tag_a_b___after_complete_job_a_with_b_child___returns_false_for_a_and_true_for_b(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_completed(self.job_a, [job('b')])

        self.assertFalse(self.tags(['a']))
        self.assertTrue(self.tags(['b']))

    def test_tag_a___after_complete_job_a_between_many_started___returns_false_because_violations_of_lifecycle_get_ignored(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_started(self.job_a)
        self.report.add_job_started(self.job_a)
        self.report.add_job_completed(self.job_a, [])
        self.report.add_job_started(self.job_a)
        self.report.add_job_started(self.job_a)
        self.report.add_job_started(self.job_a)

        self.assertFalse(self.tags(['a']))

    def test_tag_a_and_b___after_cancel_job_a_and_b___returns_false_for_both(self):
        self.report.add_job_started(self.job_a)
        self.report.add_jobs_cancelled([self.job_a, self.job_b])
        self.report.add_job_started(self.job_b)
        self.assertFalse(self.tags(['a', 'b']))

    def test_tag_a___after_start_job_a_and_retry_itself___returns_true_because_retry_on_itself_changes_nothing(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_retried(self.job_a, self.job_a, self.e)
        self.assertTrue(self.tags(['a']))

    def test_tag_a_b___after_start_job_a_and_retry_with_job_b___returns_false_on_job_a_and_true_on_job_b(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_retried(self.job_a, self.job_b, self.e)
        self.assertFalse(self.tags(['a']))
        self.assertTrue(self.tags(['b']))

    def test_tags_fetch_and_validate_file___after_retry_validate_back_to_fetch___returns_true_on_fetch_and_false_on_validate(self):
        fetch_file, validate_file = job('fetch_file'), job('validate_file')
        self.report.add_job_started(fetch_file)
        self.report.add_job_completed(fetch_file, [validate_file])  # End of fetch_file lifecycle
        self.assertFalse(self.tags(['fetch_file']))

        self.report.add_job_started(fetch_file)  # Get's ignored because the lifecycle is over
        self.assertFalse(self.tags(['fetch_file']))

        self.report.add_job_retried(validate_file, fetch_file, self.e)  # Retry to a "ended" job should reset its lifecycle
        self.assertTrue(self.tags(['fetch_file']))
        self.assertFalse(self.tags(['validate_file']))

    def test_tags_fetch_and_validate_file___after_completed_fetch_spawning_same_validate___returns_true_on_validate_and_false_on_fetch(self):
        fetch_file, validate_file = job('fetch_file'), job('validate_file')
        self.report.add_job_started(fetch_file)
        self.report.add_job_started(validate_file)
        self.report.add_job_completed(validate_file, [])  # End of validate_file lifecycle
        self.assertFalse(self.tags(['validate_file']))

        self.report.add_job_started(validate_file)  # Get's ignored because the lifecycle is over
        self.assertFalse(self.tags(['validate_file']))

        self.report.add_job_completed(fetch_file, [validate_file])  # Comtinuing to a "ended" child job resets its lifecycle
        self.assertTrue(self.tags(['validate_file']))
        self.assertFalse(self.tags(['fetch_file']))

    def test_tag_a___after_complete_job_a_continuing_on_itself___returns_true_because_self_continuing_does_not_interrupt_lifecycle(self):
        self.report.add_job_started(self.job_a)
        self.report.add_job_completed(self.job_a, [self.job_a])
        self.assertTrue(self.tags(['a']))

    def test_zip_tag___during_a_realistic_zip_install_lifecycle_with_some_retries___returns_true_during_the_transaction_and_false_outside(self):
        fetch_index, validate_index, open_zip_index, process_zip, fetch_content, validate_content, unzip_content = (job('zip') for _ in range(7))

        self.assertFalse(self.tags(['zip']))

        self.report.add_job_started(fetch_index)                                ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_retried(fetch_index, fetch_index, self.e)           ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_retried(fetch_index, fetch_index, self.e)           ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(fetch_index, [validate_index])            ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(validate_index, [open_zip_index])         ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(open_zip_index, [process_zip])            ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(process_zip, [fetch_content, self.job_a]) ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(fetch_content, [validate_content])        ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(validate_content, [unzip_content])        ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_retried(unzip_content, fetch_content, self.e)       ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(fetch_content, [validate_content])        ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(validate_content, [unzip_content])        ;  self.assertTrue(self.tags(['zip']))
        self.report.add_job_completed(unzip_content, [])

        self.assertFalse(self.tags(['zip']))

    def tags(self, tags: List[Union[int, str]]) -> bool:
        return self.report.any_in_progress_job_with_tags(tags)


class TestJob(Job):
    def __init__(self, id: int):
        self._type_id = id

    @property
    def type_id(self) -> int:
        return self._type_id

def job(tag: Union[List[Union[int, str]], Union[int, str]], id: int = 0) -> Job:
    result = TestJob(id)
    if isinstance(tag, list):
        for t in tag:
            result.add_tag(t)
    else:
        result.add_tag(tag)
    return result
