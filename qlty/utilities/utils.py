# Native libraries
import os
import uuid
import logging
# Third party libraries
import colorlog
from pprint import pformat
# Project libraries
import settings
import qlty.config as config

#: Predefined coordinate offsets for Android swipe gestures
ANDROID_SWIPE_OFFSETS = {
    'up': {
        'start_x': 0.5,
        'start_y': 0.9,  # Starting at 90% height to avoid Android navigation bar interference
        'end_x': 0.5,
        'end_y': 0
    },
    'down': {
        'start_x': 0.5,
        'start_y': 0.9,
        'end_x': 0.5,
        'end_y': 0.45
    },
    'up_30_percent': {
        'start_x': 0.5,
        'start_y': 0.8,
        'end_x': 0.5,
        'end_y': 0.5
    },
    'up_10_percent': {
        'start_x': 0.5,
        'start_y': 0.8,
        'end_x': 0.5,
        'end_y': 0.7,
    },
    'down_40_percent': {
        'start_x': 0.5,
        'start_y': 0.5,
        'end_x': 0.5,
        'end_y': 0.9
    }
}
#: Predefined coordinate offsets for iOS swipe gestures
IOS_SWIPE_OFFSETS = {
    'middle_swipe': {
        'start_x': 1,
        'start_y': 0.5,
        'end_x': 0,
        'end_y': 0.5
    },
    'up': {
        'direction': 'up'
    },
    'left': {
        'direction': 'left'
    }
}
#: Global reference to current test session identifier
CURRENT_TEST_RUN_ID = None


def setup_logger(name, debug_level):
    """
    Creates and configures a logger instance with color formatting.

    :param name: Logger identifier prefix for the formatter
    :type name: str
    :param debug_level: Logging verbosity level
    :type debug_level: int
    :return: Configured logger instance for the calling module
    :rtype: logger
    """
    # Initialize or retrieve logger by name
    new_logger = logging.getLogger(name)
    # Configure colored console output handler
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(asctime)s %(log_color)s - %(levelname)s | :%(name)s:%(message)s', datefmt='%m/%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'black,bg_red',
        },
    ))

    # Attach formatters only to newly created loggers
    if not new_logger.handlers:
        new_logger.addHandler(handler)
    new_logger.setLevel(debug_level)
    return new_logger


# Module-level logger instance
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


def get_uuid():
    """
    Generates a unique identifier using Python's uuid library

    :return: Shortened unique 6-character identifier
    :rtype: str
    """
    return '{}'.format(str(uuid.uuid4())[:6])


#: Unique identifier for current test execution session
BUILD_ID = get_uuid()


def dump_test_results(test_case):
    """
    Generates directory structure for storing individual test case results

    :param test_case: A QLTY test case instance
    :type test_case: QLTYTestCase
    :return: Absolute path to the test method results directory
    :rtype: str
    """
    class_name = test_case.__class__.__qualname__
    method_name = test_case._testMethodName

    # Build directory hierarchy
    results_dir = os.path.join(os.getcwd(), 'test_results')
    test_run_dir = os.path.join(results_dir, settings.TEST_RUN_ID)
    class_dir = os.path.join(test_run_dir, class_name)
    method_dir = os.path.join(class_dir, method_name)

    # Verify test run directory existence
    if not os.path.exists(results_dir):
        logger.debug('Test results directory missing, creating now')
        os.makedirs(test_run_dir)
        logger.debug('Test results directory created at:\n{}'.format(test_run_dir))

    # Verify class-level directory existence
    if not os.path.exists(class_dir):
        logger.debug('Test results directory for class {} not found'.format(class_name))
        os.makedirs(class_dir)
        logger.debug('{} directory created successfully'.format(class_dir))

    # Create method-specific directory
    os.makedirs(method_dir)
    logger.debug('{} directory created successfully'.format(method_dir))
    return method_dir


def dump_logs(results_dir, driver):
    """
    Extracts and saves logs to the test method results directory

    :param results_dir: Full path to test method results directory
    :type results_dir: str
    :param driver: Appium webdriver instance for log extraction
    :type driver: WebDriver
    """
    # Save page source structure
    driver_page_source_path = os.path.join(results_dir, 'page_source.txt')
    with open(driver_page_source_path, 'w') as opened_file:
        opened_file.write(pformat(driver.page_source))

    # Save platform-specific system logs
    log_path = os.path.join(results_dir, 'system.log')
    with open(log_path, 'w') as opened_file:
        if config.CURRENT_PLATFORM == 'android':
            opened_file.write(pformat(driver.get_log('logcat')))
        elif config.CURRENT_PLATFORM == 'ios':
            opened_file.write(pformat(driver.get_log('syslog')))
    logger.debug('Logs saved to: {}'.format(log_path))


def dump_screenshot(results_dir, test_case, driver):
    """
    Captures and saves screenshot when test case fails

    :param results_dir: Full path to test method results directory
    :type results_dir: str
    :param test_case: A QLTY test case instance
    :type test_case: QLTYTestCase
    :param driver: Appium webdriver instance for screenshot capture
    :type driver: WebDriver
    """
    if test_case.failureException:
        # Test method has encountered a failure
        screenshot_path = os.path.join(results_dir, 'screenshot.png')
        driver.save_screenshot(screenshot_path)
        logger.debug('Screenshot captured at: {}'.format(screenshot_path))


def exists(var):
    """
    Validates variable existence, useful for checking undefined attributes
    The variable must be passed as a reference using lambda to prevent immediate AttributeError:

        .. code-block:: python

            exists(lambda:my_variable)

    :param var: Variable reference to validate
    :return: True if variable exists, None otherwise
    :rtype: bool
    """
    try:
        return var()
    except (AttributeError, KeyError) as error:
        logger.error('Variable not found: {}'.format(error))


def get_unique_build_id():
    """
    Generates a unique build identifier for this test execution session

    :return: Unique build identifier string
    :rtype: String
    """
    return '{} {} | {}'.format(
        BUILD_ID,
        settings.PROJECT_CONFIG['PROJECT_NAME'],
        settings.PROJECT_CONFIG['RELEASE'])


def is_browser_run(platform):
    """
    Determines if current test execution targets desktop browsers

    :param platform: Platform type identifier string
    :type platform: String
    :return: True if execution targets desktop browser
    :rtype: bool
    """
    return platform == 'chrome' or platform == 'firefox'
