# Native libraries
import time
import os
import unittest
# Project libraries
from qlty.classes.core.test_runner_utils import TestRunnerUtils
from qlty.classes.core.test_reporter import TestReporter
from qlty.utilities.utils import setup_logger
import settings
import qlty.config as config
from qlty.utilities.argument_parser import QLTYArgumentParser

# Instance for collecting test case results
test_reporter = TestReporter()
# Logging instance for console output
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


def _setup():
    logger.info('Initializing test execution session')
    logger.info('Processing command line parameters')
    QLTYArgumentParser()

    # Generate unique identifier for this test session
    settings.TEST_RUN_ID = TestRunnerUtils.generate_test_run_id()
    # Begin test execution
    _execute()


def _execute():
    if config.SINGLE_TEST_NAME:
        logger.debug('Loading individual test: {}'.format(config.SINGLE_TEST_NAME))
        # For mobile web browser testing, verify the platform string contains 'web'
        if config.MOBILE_BROWSER:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.mobile_web.' + config.SINGLE_TEST_NAME)
        elif config.DESKTOP_BROWSER:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.web.' + config.SINGLE_TEST_NAME)
        else:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.' + config.CURRENT_PLATFORM + '.' + config.SINGLE_TEST_NAME)
    else:
        logger.debug('Loading full test collection')
        test_suite = unittest.TestLoader().discover(os.path.join(os.getcwd(), 'tests'))

    # Begin timing test execution
    test_run_start_time = time.time()
    logger.debug('Starting test execution')
    try:
        results = unittest.TextTestRunner(verbosity=1).run(test_suite)
        logger.debug('Test execution completed successfully')
    except Exception as error:
        logger.critical('Test execution encountered an error: {}'.format(str(error)))
        exit(1)

    # Calculate total execution duration
    test_run_elapsed_time = time.time() - test_run_start_time

    _report(results, test_run_elapsed_time)


def _report(results, test_run_elapsed_time):
    # Collect all test case results including failures and errors
    test_reporter.get_results(results)
    # Generate and distribute reports
    logger.debug('Generating test reports for results :\n{}'.format(test_reporter.test_results))
    TestRunnerUtils.report(test_reporter.test_results, settings.TEST_RUN_ID, test_run_elapsed_time)


def qlty():
    _setup()
