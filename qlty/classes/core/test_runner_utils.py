# Native libraries
import pwd
import os
from pprint import pformat
from datetime import datetime
# Project libraries
from qlty.classes.integrations.slack_integration import SlackIntegration
from qlty.classes.integrations.testrail_integration import TestRailIntegration
from qlty.utilities.utils import setup_logger, get_unique_build_id
import qlty.config as config
import settings

logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class TestRunnerUtils:
    """
    Utility class for configuration validation and test run lifecycle management
    """

    #: Console message for iOS-only test execution
    running_on_ios_message = 'iOS test cases only, skipping'
    #: Console message for Android-only test execution
    running_on_android_message = 'Android test cases only, skipping'
    #: Console message for Android web test execution
    running_on_android_web_message = 'Chrome mobile for Android only, skipping'
    #: Console message for iOS web test execution
    running_on_ios_web_message = 'Safari for iOS only, skipping'

    @staticmethod
    def report(test_results, test_run_id, test_run_elapsed_time):
        """
        Distributes results to enabled integration systems

        :param test_results: Collection of test execution results
        :type test_results: dict
        :param test_run_id: Unique test run identifier
        :type test_run_id: str
        :param test_run_elapsed_time: Total test run duration
        :type test_run_elapsed_time: datetime
        """

        # Submit test results to TestRail first if enabled (to get run_id for Slack)
        testrail_run_id = None
        if config.TESTRAIL_INTEGRATION:
            testrail_run_id = TestRunnerUtils._report_to_testrail(test_results, test_run_id, test_run_elapsed_time)

        # Dispatch Slack notification if enabled (with TestRail run_id if available)
        if config.SLACK_REPORTING:
            SlackIntegration().report(
                TestRunnerUtils.get_testrun_totals(test_results),
                TestRunnerUtils.get_readable_run_time(test_run_elapsed_time),
                testrail_run_id,
                test_run_id
            )

        # Display Saucelabs results link if integration active
        if config.SAUCELABS_INTEGRATION:
            logger.info('Saucelabs results: {}\n Search for test cases with prefix: {}'.format(
                settings.SAUCELABS['URL'], get_unique_build_id()))

    @staticmethod
    def generate_test_run_id():
        """
        Generates unique identifier string for test run

        :return: Test run identifier string
        :rtype: str
        """
        from qlty.utilities.utils import BUILD_ID

        project_name = settings.PROJECT_CONFIG.get('PROJECT_NAME', 'QLTY').upper()
        platform = config.CURRENT_PLATFORM.upper()
        start_time = datetime.now().strftime('%H:%M:%S')
        user = pwd.getpwuid(os.getuid())[0]

        return '{} {} running on {} | started at [{}] by {}'.format(
            BUILD_ID, project_name, platform, start_time, user
        )

    @staticmethod
    def running_on_ios():
        """
        Checks if current test run targets iOS platform

        :return: True if iOS execution, False otherwise
        :rtype: bool
        """
        return config.CURRENT_PLATFORM == 'ios'

    @staticmethod
    def running_on_android():
        """
        Checks if current test run targets Android platform

        :return: True if Android execution, False otherwise
        :rtype: bool
        """
        return config.CURRENT_PLATFORM == 'android'

    @staticmethod
    def running_on_android_web():
        """
        Checks if current test run targets Chrome mobile for Android

        :return: True if Android web execution, False otherwise
        :rtype: bool
        """
        return config.CURRENT_PLATFORM == 'android_web'

    @staticmethod
    def running_on_ios_web():
        """
        Checks if current test run targets Safari mobile for iOS

        :return: True if iOS web execution, False otherwise
        :rtype: bool
        """
        return config.CURRENT_PLATFORM == 'ios_web'

    @staticmethod
    def get_testrun_totals(test_results):
        """
        Generates consolidated test case execution statistics

        Example output:

            .. code-block:: python

                results = {
                    'total_testcases': 0,
                    'passed_testcases': 0,
                    'failed_testcases': 0
                }

        :param test_results: Collection of executed test cases
        :type: Dictionary
        :return: Consolidated statistics dictionary
        :rtype: Dictionary
        """

        results = {
            'total_testcases': 0,
            'passed_testcases': 0,
            'failed_testcases': 0,
            'passed_percentage': '0.0%',
            'failed_percentage': '0.0%',
        }

        # Aggregate test result statistics
        for test_class, test_methods in test_results.items():
            for test_method, result in test_methods.items():
                if result['status'] == 'passed':
                    results['passed_testcases'] += 1
                elif result['status'] == 'failed':
                    results['failed_testcases'] += 1
                else:
                    logger.warning('Unrecognized result status: {}'.format(result['status']))

        # Calculate totals and percentages
        results['total_testcases'] = results['passed_testcases'] + results['failed_testcases']
        # Calculate pass/fail percentages
        results['passed_percentage'] = "{:.1f}%".format((results['passed_testcases'] / results['total_testcases']) * 100)
        results['failed_percentage'] = "{:.1f}%".format((results['failed_testcases'] / results['total_testcases']) * 100)

        return results

    @staticmethod
    def get_readable_run_time(test_run_time):
        """
        Converts test run duration to human-readable format (e.g., 1h 12m 34s)

        :param test_run_time: Test run duration in seconds
        :return: Formatted duration string
        :rtype: String
        """

        result = ''
        # Extract hours component (floor division)
        if test_run_time // 3600 > 0:
            result += '{}h '.format(int(test_run_time // 3600))
        # Remove hours from remaining time
        test_run_time %= 3600
        # Extract minutes component
        if test_run_time // 60 > 0:
            result += '{}m '.format(int(test_run_time // 60))
        # Remove minutes from remaining time
        test_run_time %= 60
        # Append remaining seconds
        result += '{}s'.format(int(test_run_time))

        return result

    @staticmethod
    def _report_to_testrail(test_results, test_run_id, test_run_elapsed_time):
        """
        Submits test results to TestRail test management system

        :param test_results: Collection of test execution results
        :type test_results: dict
        :param test_run_id: Unique test run identifier
        :type test_run_id: str
        :param test_run_elapsed_time: Total test run duration in seconds
        :type test_run_elapsed_time: float
        :return: TestRail run ID
        :rtype: int
        """
        try:
            # Initialize TestRail integration
            logger.info('Initializing TestRail integration...')
            testrail = TestRailIntegration()

            # Collect all case IDs that will be tested BEFORE creating the run
            case_ids_to_test = []
            for test_class, test_methods in test_results.items():
                for test_method, result in test_methods.items():
                    # Include test cases with associated TestRail case IDs
                    if result.get('test_case_ids') and len(result['test_case_ids']) > 0:
                        case_ids_to_test.extend(result['test_case_ids'])

            # Remove duplicates while preserving order
            case_ids_to_test = list(dict.fromkeys(case_ids_to_test))
            logger.debug('Found {} test case(s) to report: {}'.format(len(case_ids_to_test), case_ids_to_test))

            # Create test run in TestRail with only the cases that were tested
            # test_run_id already contains: PROJECT | PLATFORM | [TIME] - USER
            run_name = test_run_id
            run_description = 'Automated test run\nPlatform: {}\nDuration: {}'.format(
                config.CURRENT_PLATFORM,
                TestRunnerUtils.get_readable_run_time(test_run_elapsed_time)
            )

            test_run = testrail.create_test_run(run_name, run_description, case_ids=case_ids_to_test)
            run_id = test_run['id']

            # Submit results for each test case
            for test_class, test_methods in test_results.items():
                for test_method, result in test_methods.items():
                    # Skip test cases without associated TestRail case IDs
                    if not result.get('test_case_ids') or len(result['test_case_ids']) == 0:
                        logger.debug('Skipping {} - no TestRail case IDs associated'.format(test_method))
                        continue

                    # Submit result for each associated case ID
                    for case_id in result['test_case_ids']:
                        try:
                            # Map framework status to TestRail status
                            status = result['status']
                            comment = result.get('message', '')
                            elapsed = TestRunnerUtils.get_readable_run_time(result['duration']) if result.get('duration') else None

                            # Add test class and method name to comment
                            test_identifier = '{}.{}'.format(test_class, test_method)
                            if comment:
                                comment = 'Test: {}\n\n{}'.format(test_identifier, comment)
                            else:
                                comment = 'Test: {}'.format(test_identifier)

                            # Submit result to TestRail
                            testrail.add_result_for_case(run_id, case_id, status, comment, elapsed)

                        except Exception as e:
                            logger.error('Failed to add result for case {}: {}'.format(case_id, str(e)))

            logger.info('TestRail reporting completed successfully')
            logger.info('View results at: {}/index.php?/runs/view/{}'.format(
                settings.TESTRAIL['BASE_URL'].rstrip('/'), run_id))

            return run_id

        except Exception as e:
            logger.error('TestRail integration failed: {}'.format(str(e)))
            logger.warning('Continuing execution despite TestRail failure')
            return None
