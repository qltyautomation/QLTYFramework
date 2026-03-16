# Native libraries
import time
import os
import sys
import logging
import tempfile
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
# Log capture state (initialized in _setup)
_log_path = None
_stop_capture = lambda: None


def _setup():
    logger.info('Initializing test execution session')

    # Reset reporter state so a second qlty() call in the same process starts clean
    test_reporter.test_results = {}
    test_reporter.external_case_ids = {}

    logger.info('Processing command line parameters')
    QLTYArgumentParser()

    # Start capturing console output to a log file
    global _log_path, _stop_capture
    _log_path, _stop_capture = _start_log_capture()

    # Generate unique identifier for this test session
    settings.TEST_RUN_ID = TestRunnerUtils.generate_test_run_id()

    # Register lifecycle integrations and validate their config
    _register_integrations()


def _register_integrations():
    """Register enabled integrations and validate their config before tests run."""
    from qlty.classes.integrations import registry

    registry.clear()

    if config.TESTRAIL_INTEGRATION:
        from qlty.classes.integrations.testrail_integration import TestRailIntegration
        registry.register(TestRailIntegration())

    if config.SLACK_REPORTING:
        from qlty.classes.integrations.slack_integration import SlackIntegration
        registry.register(SlackIntegration())

    # Register project-level custom integrations from settings.CUSTOM_INTEGRATIONS.
    # Entries can be Integration instances or dotted path strings
    # (e.g. 'integrations.my_module.MyIntegration') to avoid circular imports.
    for entry in getattr(settings, 'CUSTOM_INTEGRATIONS', []):
        if isinstance(entry, str):
            module_path, class_name = entry.rsplit('.', 1)
            import importlib
            module = importlib.import_module(module_path)
            integration = getattr(module, class_name)()
        else:
            integration = entry
        registry.register(integration)

    # Validate all integrations — failed ones are deregistered,
    # required ones abort the run if they fail
    registry.on_run_start()


def _filter_excluded_tests(test_suite):
    """
    Recursively removes test cases whose class name is in config.EXCLUDE_TESTS.

    :param test_suite: unittest.TestSuite to filter
    :return: Filtered unittest.TestSuite
    """
    filtered = unittest.TestSuite()
    for test in test_suite:
        if isinstance(test, unittest.TestSuite):
            filtered.addTests(_filter_excluded_tests(test))
        else:
            if test.__class__.__name__ not in config.EXCLUDE_TESTS:
                filtered.addTest(test)
    return filtered


def _filter_by_tags(test_suite, _default_exclude=None):
    """
    Recursively filters test cases based on class-level tags set by the @tag() decorator.

    Filtering logic:
        1. If --tag is set: keep ONLY test classes whose _tags contain the specified tag
        2. Else if --exclude-tag is set: exclude test classes whose _tags contain the specified tag
        3. Else: auto-exclude test classes tagged with any tag in DEFAULT_EXCLUDE_TAGS

    :param test_suite: unittest.TestSuite to filter
    :return: Filtered unittest.TestSuite
    """
    if _default_exclude is None:
        _default_exclude = set(settings.PROJECT_CONFIG.get('DEFAULT_EXCLUDE_TAGS', []))

    filtered = unittest.TestSuite()
    for test in test_suite:
        if isinstance(test, unittest.TestSuite):
            filtered.addTests(_filter_by_tags(test, _default_exclude))
        else:
            test_tags = getattr(test.__class__, '_tags', set())
            if config.INCLUDE_TAG:
                # Include ONLY classes with the specified tag
                if config.INCLUDE_TAG in test_tags:
                    filtered.addTest(test)
            elif config.EXCLUDE_TAG:
                # Exclude classes with the specified tag
                if config.EXCLUDE_TAG not in test_tags:
                    filtered.addTest(test)
            else:
                # Auto-exclude classes tagged with any DEFAULT_EXCLUDE_TAGS
                if not test_tags.intersection(_default_exclude):
                    filtered.addTest(test)
    return filtered


class _TeeStream:
    """Writes to both the original stream and a log file."""
    def __init__(self, original, log_file):
        self.original = original
        self.log_file = log_file
        self._active = True

    def write(self, data):
        self.original.write(data)
        if self._active:
            self.log_file.write(data)

    def flush(self):
        self.original.flush()
        if self._active:
            self.log_file.flush()

    def stop(self):
        """Stop writing to the log file."""
        self._active = False


def _start_log_capture():
    """
    Starts capturing all console output (logger + unittest) to a temp file.
    Returns the log file path and a cleanup function.
    """
    log_path = os.path.join(tempfile.gettempdir(), 'qlty_test_run.log')
    log_file = open(log_path, 'w')

    # Add a FileHandler to the root logger to capture all logger output
    file_handler = logging.FileHandler(log_path, mode='a')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s | :%(name)s:%(message)s', datefmt='%m/%d %H:%M:%S'
    ))
    logging.getLogger().addHandler(file_handler)

    # Tee stderr to capture unittest TextTestRunner output
    tee = _TeeStream(sys.stderr, log_file)
    sys.stderr = tee

    def cleanup():
        tee.stop()
        logging.getLogger().removeHandler(file_handler)
        file_handler.close()
        log_file.close()

    return log_path, cleanup


def _execute():
    if config.SINGLE_TEST_NAME:
        logger.debug('Loading individual test: {}'.format(config.SINGLE_TEST_NAME))
        # Format test name to include module prefix if needed
        formatted_test_name = TestRunnerUtils.format_single_test_name(config.SINGLE_TEST_NAME)
        # For mobile web browser testing, verify the platform string contains 'web'
        if config.MOBILE_BROWSER:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.mobile_web.' + formatted_test_name)
        elif config.DESKTOP_BROWSER:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.web.' + formatted_test_name)
        else:
            test_suite = unittest.TestLoader().loadTestsFromName(
                name='tests.' + config.CURRENT_PLATFORM + '.' + formatted_test_name)
    else:
        logger.debug('Loading full test collection')
        test_suite = unittest.TestLoader().discover(os.path.join(os.getcwd(), 'tests'))

    # Apply exclusion filter if --exclude was specified
    if config.EXCLUDE_TESTS:
        test_suite = _filter_excluded_tests(test_suite)
        logger.debug('Excluded test classes: {}'.format(', '.join(config.EXCLUDE_TESTS)))

    # Apply tag-based filtering (only for full suite runs, not single tests)
    if not config.SINGLE_TEST_NAME:
        test_suite = _filter_by_tags(test_suite)
        if config.INCLUDE_TAG:
            logger.debug('Filtering to tests tagged: {}'.format(config.INCLUDE_TAG))
        elif config.EXCLUDE_TAG:
            logger.debug('Excluding tests tagged: {}'.format(config.EXCLUDE_TAG))
        else:
            default_exclude = settings.PROJECT_CONFIG.get('DEFAULT_EXCLUDE_TAGS', [])
            if default_exclude:
                logger.debug('Auto-excluding tests tagged: {}'.format(', '.join(default_exclude)))

    # Begin timing test execution
    test_run_start_time = time.time()
    logger.debug('Starting test execution')
    try:
        results = unittest.TextTestRunner(verbosity=1).run(test_suite)
        logger.debug('Test execution completed successfully')
    except Exception as error:
        logger.critical('Test execution encountered an error: {}'.format(str(error)))
        results = None

    # Calculate total execution duration
    test_run_elapsed_time = time.time() - test_run_start_time

    # Stop capture before reporting so the log file is complete
    _stop_capture()

    if results is not None:
        _report(results, test_run_elapsed_time, _log_path)
    else:
        # Still attempt reporting so integrations can notify about the failure
        logger.warning('Test execution failed — attempting to report available results')
        test_reporter.test_results = test_reporter.test_results or {}
        TestRunnerUtils.report(test_reporter.test_results, settings.TEST_RUN_ID, test_run_elapsed_time, _log_path)
        sys.exit(1)


def _report(results, test_run_elapsed_time, log_path=None):
    # Collect all test case results including failures and errors
    test_reporter.get_results(results)
    # Generate and distribute reports
    logger.debug('Generating test reports for results :\n{}'.format(test_reporter.test_results))
    TestRunnerUtils.report(test_reporter.test_results, settings.TEST_RUN_ID, test_run_elapsed_time, log_path)


def qlty():
    _setup()
    _execute()
