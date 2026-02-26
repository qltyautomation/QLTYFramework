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
        testrail_run_ids = None
        if config.TESTRAIL_INTEGRATION:
            testrail_run_ids = TestRunnerUtils._report_to_testrail(test_results, test_run_id, test_run_elapsed_time)

        # Dispatch Slack notification if enabled (with TestRail run_id if available)
        if config.SLACK_REPORTING:
            # Slack expects a single run ID — use the first one from the list
            testrail_run_id = testrail_run_ids[0] if testrail_run_ids else None
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

        # Aggregate test result statistics by counting test case IDs
        for test_class, test_methods in test_results.items():
            for test_method, result in test_methods.items():
                # Count test case IDs instead of test methods
                case_count = len(result.get('test_case_ids', [])) or 1
                if result['status'] == 'passed':
                    results['passed_testcases'] += case_count
                elif result['status'] == 'failed':
                    results['failed_testcases'] += case_count
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
        Submits test results to TestRail test management system.
        Groups test cases by suite ID and creates separate test runs per suite.

        :param test_results: Collection of test execution results
        :type test_results: dict
        :param test_run_id: Unique test run identifier
        :type test_run_id: str
        :param test_run_elapsed_time: Total test run duration in seconds
        :type test_run_elapsed_time: float
        :return: List of TestRail run IDs created
        :rtype: list[int]
        """
        # Check for failures and respect REPORT_ON_FAIL setting
        totals = TestRunnerUtils.get_testrun_totals(test_results)
        if totals['failed_testcases'] > 0:
            if not config.REPORT_ON_FAIL:
                logger.warning('Failed test results detected, skipping TestRail reporting')
                return None
            else:
                logger.warning('Forcing TestRail reporting despite failed results')

        try:
            # Initialize TestRail integration
            logger.info('Initializing TestRail integration...')
            testrail = TestRailIntegration()

            # Group case IDs by suite ID (None = default suite from settings)
            from collections import defaultdict
            suite_cases = defaultdict(list)

            for test_class, test_methods in test_results.items():
                for test_method, result in test_methods.items():
                    if result.get('test_case_ids') and len(result['test_case_ids']) > 0:
                        suite_id = result.get('suite_id')  # None means default suite
                        suite_cases[suite_id].extend(result['test_case_ids'])

            # Deduplicate per suite while preserving order
            for suite_id in suite_cases:
                suite_cases[suite_id] = list(dict.fromkeys(suite_cases[suite_id]))

            if not suite_cases:
                logger.warning('No test cases with TestRail IDs found, skipping reporting')
                return None

            # Log suite grouping
            for suite_id, case_ids in suite_cases.items():
                suite_label = 'default (suite {})'.format(settings.TESTRAIL['SUITE_ID']) if suite_id is None else 'suite {}'.format(suite_id)
                logger.debug('Suite {}: {} case(s) — {}'.format(suite_label, len(case_ids), case_ids))

            # test_run_id already contains: PROJECT | PLATFORM | [TIME] - USER
            run_name = test_run_id

            # Build a detailed description for the TestRail run
            environment_name = config.CURRENT_ENVIRONMENT or 'N/A'
            environment_url = ''
            if hasattr(settings, 'ENVIRONMENTS') and config.CURRENT_ENVIRONMENT:
                env_config = settings.ENVIRONMENTS.get(config.CURRENT_ENVIRONMENT, {})
                environment_url = env_config.get('BASE_URL', '')

            project_config = getattr(settings, 'PROJECT_CONFIG', {})
            release = project_config.get('RELEASE', 'N/A')
            source_repo = project_config.get('SOURCE_REPO', '')
            executed_by = pwd.getpwuid(os.getuid())[0]

            description_lines = [
                'Automated test run',
                'Platform: {}'.format(config.CURRENT_PLATFORM),
                'Environment: {}'.format(environment_name),
            ]
            if environment_url:
                description_lines.append('URL: {}'.format(environment_url))
            description_lines.append('Release: {}'.format(release))
            description_lines.append('Duration: {}'.format(
                TestRunnerUtils.get_readable_run_time(test_run_elapsed_time)))
            description_lines.append('Executed by: {}'.format(executed_by))
            if config.HEADLESS:
                description_lines.append('Mode: Headless')
            if source_repo:
                description_lines.append('Source: {}'.format(source_repo))

            run_description = '\n'.join(description_lines)

            # Create one test run per suite and submit results
            run_ids = []
            for suite_id, case_ids in suite_cases.items():
                suite_label = 'default' if suite_id is None else 'suite {}'.format(suite_id)
                logger.info('Creating TestRail run for {} with {} case(s)'.format(suite_label, len(case_ids)))

                test_run = testrail.create_test_run(run_name, run_description, case_ids=case_ids, suite_id=suite_id)
                run_id = test_run['id']
                run_ids.append(run_id)

                # Build set of case IDs in this suite for fast lookup
                suite_case_set = set(case_ids)

                # Submit results for test cases belonging to this suite
                for test_class, test_methods in test_results.items():
                    for test_method, result in test_methods.items():
                        if not result.get('test_case_ids') or len(result['test_case_ids']) == 0:
                            continue

                        # Only submit if this result belongs to the current suite
                        result_suite_id = result.get('suite_id')
                        if result_suite_id != suite_id:
                            continue

                        for case_id in result['test_case_ids']:
                            if case_id not in suite_case_set:
                                continue

                            try:
                                status = result['status']
                                comment = result.get('message', '')
                                elapsed = TestRunnerUtils.get_readable_run_time(result['duration']) if result.get('duration') else None

                                test_identifier = '{}.{}'.format(test_class, test_method)
                                if comment:
                                    comment = 'Test: {}\n\n{}'.format(test_identifier, comment)
                                else:
                                    comment = 'Test: {}'.format(test_identifier)

                                testrail_result = testrail.add_result_for_case(run_id, case_id, status, comment, elapsed)

                                # Attach screenshots and logs to the result
                                result_id = testrail_result.get('id')
                                results_dir = result.get('results_dir')
                                if result_id and results_dir:
                                    for filename in ['screenshot.png', 'system.log', 'page_source.txt']:
                                        file_path = os.path.join(results_dir, filename)
                                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                            try:
                                                testrail.add_attachment_to_result(result_id, file_path)
                                            except Exception as attach_err:
                                                logger.warning('Failed to attach {} for case {}: {}'.format(
                                                    filename, case_id, str(attach_err)))

                            except Exception as e:
                                logger.error('Failed to add result for case {}: {}'.format(case_id, str(e)))

                logger.info('View results at: {}/index.php?/runs/view/{}'.format(
                    settings.TESTRAIL['BASE_URL'].rstrip('/'), run_id))

            logger.info('TestRail reporting completed successfully — {} run(s) created'.format(len(run_ids)))
            return run_ids

        except Exception as e:
            logger.error('TestRail integration failed: {}'.format(str(e)))
            logger.warning('Continuing execution despite TestRail failure')
            return None
