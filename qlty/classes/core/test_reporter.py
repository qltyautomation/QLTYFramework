# Native libraries
import datetime
# Project libraries
import string

import settings

from qlty.classes.core.test_target import TestTarget
from qlty.utilities.utils import setup_logger

# Configure logging instance
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class TestReporter:
    """
    Manages test suite and test case result collection and tracking
    """

    #: Dictionary containing results for all test cases
    test_results = {}
    #: Dictionary storing external test case identifiers
    external_case_ids = {}

    def register_test_case(self, test_case, case_ids: list[int], feature_name: string,
                           test_target: TestTarget, suite_id=None):
        """
        Registers test case with associated metadata for reporting

        :param test_case: Test case instance extending unittest TestCase
        :type test_case: QLTYTestCase
        :param case_ids: List of test case identifiers for external tracking
        :type case_ids: list
        :param feature_name: Feature identifier for this test case
        :type feature_name: String
        :param test_target: Test execution target (UI or API)
        :type test_target: Enum[TestTarget]
        :param suite_id: TestRail suite ID override (optional, defaults to settings.TESTRAIL['SUITE_ID'])
        :type suite_id: int or None
        """
        # Register test case in results
        self._add_test_case(test_case, feature_name, test_target, suite_id)
        # Associate external tracking identifiers with test case
        self._add_external_test_case_ids(test_case, case_ids)

    def _add_external_test_case_ids(self, test_case, case_ids):
        """
        Associates external tracking case identifiers with specified test case

        :param test_case: Test case instance extending unittest TestCase
        :type test_case: QLTYTestCase
        :param case_ids: List of test case identifiers for external tracking
        :type case_ids: list
        """
        logger.debug('Test case [{}] associated with test case IDs: {}'.format(test_case, case_ids))
        test_class = test_case.__class__.__qualname__
        test_method_name = test_case._testMethodName
        self.test_results[test_class][test_method_name]['test_case_ids'] = case_ids
        for case_id in case_ids:
            self.external_case_ids[case_id] = case_id

    def add_test_case_result(self, test_case_result):
        """
        Records test case execution results
        Only successful passes are recorded here; failures captured at test run completion

        :param test_case_result: Test case instance extending unittest TestCase
        :type test_case_result: QLTYTestCase
        """
        test_class = test_case_result.__class__.__qualname__
        test_method_name = test_case_result._testMethodName
        # Calculate test case execution duration
        self.test_results[test_class][test_method_name]['end_time'] = datetime.datetime.now()
        self.test_results[test_class][test_method_name]['duration'] = \
            int((self.test_results[test_class][test_method_name]['end_time'] -
                 self.test_results[test_class][test_method_name]['start_time']).total_seconds())

        if test_case_result._outcome is not None:
            if test_case_result._outcome.success:
                self.test_results[test_class][test_method_name]['status'] = 'passed'

    def _add_test_case(self, test_case, feature_name, test_target, suite_id=None):
        """
        Creates new test case entry in results dictionary

        :param test_case: Test case instance extending unittest TestCase
        :type test_case: QLTYTestCase
        :param suite_id: TestRail suite ID override (optional)
        :type suite_id: int or None
        """
        if self.test_results.get(test_case.__class__.__qualname__) is None:
            # Initialize test class entry if not present
            self.test_results[test_case.__class__.__qualname__] = {}

        # Create test case entry under class name
        self.test_results[test_case.__class__.__qualname__][test_case._testMethodName] = {
            'status': 'untested',
            'start_time': datetime.datetime.now(),
            'end_time': None,
            'duration': None,
            'test_case_ids': [],
            'suite_id': suite_id,
            'message': '',
            'feature_name': feature_name,
            'test_target': test_target,
            'results_dir': None
        }

    def get_results(self, results):
        """
        Extracts failure and error results from test execution

        :param results: unittest TextTestResult object
        :type results: TextTestResult
        """
        # Process failed test cases
        self._get_failed_results(results.failures)
        # Process error test cases
        self._get_failed_results(results.errors)

    def _get_failed_results(self, result_list):
        """
        Extracts result data from failed and error test cases

        :param result_list: List of tuples containing (test case, stack trace)
        :type result_list: list
        """
        for failed_case in result_list:
            # Each tuple contains (test case, stack trace)
            test_case = failed_case[0]
            stack_trace = failed_case[1]
            # Extract test class and method identifiers
            test_class = test_case.__class__.__qualname__
            if test_class == '_ErrorHolder':
                # setUp method failure detected (class or test case level)
                logger.critical('SetUp method failure for Class or Test Case: {}'.format(test_case.description))
                return
            test_method_name = test_case._testMethodName
            # Record failure status and stack trace
            self.test_results[test_class][test_method_name]['status'] = 'failed'
            self.test_results[test_class][test_method_name]['message'] = stack_trace
