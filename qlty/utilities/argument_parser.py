# Native libraries
import argparse
# Project libraries
import os

from qlty.utilities.utils import setup_logger, exists
from qlty.classes.core.test_runner_utils import TestRunnerUtils
import settings
import qlty.config as config

# Initialize logging instance
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class QLTYArgumentParser:
    """
    Command line argument parser for the QLTY test execution framework
    """

    def __init__(self):
        """
        Initialize argument parser and process command line inputs
        """
        self.parser = argparse.ArgumentParser()
        self._prepare_arguments()
        self._parse_arguments()
        self._validate_arguments()
        self._print_arguments()

    def _prepare_arguments(self):
        """
        Configures all supported command line arguments for the parser
        """
        # Define all available command line arguments
        # Platform selection
        self.parser.add_argument('-p', '--platform', default=None, help='Target platform for automation: [ios | android]',
                                 choices=['ios', 'android', 'android_web', 'ios_web', 'chrome', 'firefox'],
                                 required=True, dest='platform')
        self.parser.add_argument('-s', '--slack', default=False, help='Enable Slack notifications for test results',
                                 required=False, dest='slack_reporting', action='store_true')
        self.parser.add_argument('-t', '--test', default=None, help='Execute a specific test case', required=False,
                                 dest='single_test')
        self.parser.add_argument('-u', '--update-automation', default=False,
                                 help='Update automation flags for executed test cases', required=False,
                                 dest='update_automation', action='store_true')
        self.parser.add_argument('-f', '--report-on-fail', default=False, help='Generate reports even for failed tests',
                                 required=False, dest='report_on_fail', action='store_true')
        self.parser.add_argument('-l', '--saucelabs', default=False,
                                 help='Execute tests on Saucelabs cloud platform', required=False,
                                 dest='saucelabs', action='store_true')
        self.parser.add_argument('-r', '--testrail', default=False,
                                 help='Enable TestRail integration for test result reporting', required=False,
                                 dest='testrail', action='store_true')
        self.parser.add_argument('-d', '--managed', default=False,
                                 help='Use automated driver management', required=False,
                                 dest='managed_drivers', action='store_true')
        self.parser.add_argument('--headless', default=False,
                                 help='Run browser in headless mode (no UI)', required=False,
                                 dest='headless', action='store_true')
        self.parser.add_argument('--base-url', default=None,
                                 help='Override base URL for target environment', required=False,
                                 dest='base_url')

    def _parse_arguments(self):
        """
        Processes command line arguments and maps them to configuration settings
        """
        # Extract parsed arguments
        args = self.parser.parse_args()

        # Map arguments to configuration variables
        config.CURRENT_PLATFORM = args.platform
        config.SLACK_REPORTING = args.slack_reporting
        config.SINGLE_TEST_NAME = args.single_test
        config.UPDATE_AUTOMATION = args.update_automation
        config.REPORT_ON_FAIL = args.report_on_fail
        config.SAUCELABS_INTEGRATION = args.saucelabs
        config.TESTRAIL_INTEGRATION = args.testrail
        config.MANAGED_DRIVERS = args.managed_drivers
        config.HEADLESS = args.headless
        config.BASE_URL = args.base_url

        # Override environment base URL if --base-url was provided
        if args.base_url:
            env = settings.PROJECT_CONFIG.get('ENVIRONMENT', 'STAGING')
            if env in settings.ENVIRONMENTS:
                settings.ENVIRONMENTS[env]['BASE_URL'] = args.base_url

        config.MOBILE_BROWSER = False
        config.DESKTOP_BROWSER = False

        # Detect mobile browser testing mode
        if 'android_web' in args.platform or 'ios_web' in args.platform:
            config.MOBILE_BROWSER = True
        # Detect desktop browser testing mode
        if 'chrome' in args.platform or 'firefox' in args.platform:
            config.DESKTOP_BROWSER = True

    def _print_arguments(self):
        """
        Outputs current configuration state for debugging purposes
        """
        logger.debug('Target platform: {}'.format(config.CURRENT_PLATFORM))
        logger.debug('Managed drivers enabled: {}'.format(config.MANAGED_DRIVERS))
        logger.debug('Slack reporting enabled: {}'.format(config.SLACK_REPORTING))
        logger.debug('Single test execution: {}'.format(config.SINGLE_TEST_NAME))
        logger.debug('Report on failure: {}'.format(config.REPORT_ON_FAIL))
        logger.debug('Saucelabs Integration enabled: {}'.format(config.SAUCELABS_INTEGRATION))
        logger.debug('TestRail Integration enabled: {}'.format(config.TESTRAIL_INTEGRATION))
        logger.debug('Mobile browser mode: {}'.format(config.MOBILE_BROWSER))
        if config.BASE_URL:
            logger.debug('Base URL override: {}'.format(config.BASE_URL))
        logger.debug('Jenkins execution detected: {}'.format(config.RUNNING_ON_JENKINS))

    def _validate_arguments(self):
        """
        Validates that required settings exist in settings.py for selected integrations
        """
        # Configure reporting behavior
        if not config.REPORT_ON_FAIL:
            logger.info('Reporting enabled only for successful test executions')
        else:
            logger.info('Reporting enabled regardless of test execution outcome')

        missing_settings = False
        # Validate platform capabilities configuration
        # Verify capabilities structure exists
        if exists(lambda: settings.SELENIUM['CAPABILITIES']) is None:
            logger.error('No capabilities configured in `settings.py` file')
            missing_settings = True

        # Validate platform-specific capabilities
        if exists(lambda: settings.SELENIUM['CAPABILITIES'][config.CURRENT_PLATFORM]) is None\
                and not config.MANAGED_DRIVERS:
            logger.error('Missing capability configuration for `{}` in `settings.py` file'.format(
                config.CURRENT_PLATFORM))
            missing_settings = True

        # Validate Slack integration requirements
        if config.SLACK_REPORTING:
            if exists(lambda: settings.SLACK['SLACK_AUTH_TOKEN']) is None:
                logger.error('Slack integration requires authentication token environment variable')
                missing_settings = True
            if exists(lambda: settings.SLACK['CHANNEL_ID']) is None:
                logger.error('Slack integration requires channel id configuration in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.PROJECT_CONFIG['RELEASE']) is None:
                logger.error('Slack integration requires RELEASE configuration in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.PROJECT_CONFIG['PROJECT_NAME']) is None:
                logger.error('Slack integration requires PROJECT_NAME configuration in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.PROJECT_CONFIG['ENVIRONMENT']) is None:
                logger.error('Slack integration requires ENVIRONMENT configuration in `settings.py` file')
                missing_settings = True

        # Validate Saucelabs integration requirements
        if config.SAUCELABS_INTEGRATION and not config.MANAGED_DRIVERS:
            # Verify Saucelabs-specific capability configuration
            if exists(lambda: settings.SELENIUM['CAPABILITIES'][config.CURRENT_PLATFORM + '_saucelabs']) is None:
                logger.error(
                    'Missing capability configuration for `{}_saucelabs` in `settings.py` file'.format(
                        config.CURRENT_PLATFORM))
                missing_settings = True

            if exists(lambda: settings.SAUCELABS['USERNAME']) is None:
                logger.error('Saucelabs integration requires USERNAME in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.SAUCELABS['ACCESS_KEY']) is None:
                logger.error('Saucelabs integration requires ACCESS_KEY configuration in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.SAUCELABS['URL']) is None:
                logger.error('Saucelabs integration requires URL in `settings.py` file')
                missing_settings = True

        # Validate TestRail integration requirements
        if config.TESTRAIL_INTEGRATION:
            if exists(lambda: settings.TESTRAIL['BASE_URL']) is None:
                logger.error('TestRail integration requires BASE_URL in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.TESTRAIL['USERNAME']) is None:
                logger.error('TestRail integration requires USERNAME in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.TESTRAIL['API_KEY']) is None:
                logger.error('TestRail integration requires API_KEY in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.TESTRAIL['PROJECT_ID']) is None:
                logger.error('TestRail integration requires PROJECT_ID in `settings.py` file')
                missing_settings = True
            if exists(lambda: settings.TESTRAIL['SUITE_ID']) is None:
                logger.error('TestRail integration requires SUITE_ID in `settings.py` file')
                missing_settings = True

        # Validate Jenkins environment configuration
        if os.getenv('JENKINS_URL', None):
            logger.info('Jenkins execution detected: [{}]'.format(
                os.getenv('JENKINS_URL', 'Could not retrieve JENKINS_URL')))
            config.RUNNING_ON_JENKINS = True
            if exists(lambda: settings.JENKINS['JOBS'][config.CURRENT_PLATFORM]) is None:
                logger.error('Jenkins execution requires relative job url configuration in `settings.py` file')
                missing_settings = True

        # Abort execution if required settings are missing
        if missing_settings:
            logger.error('One or more required settings are missing from `settings.py` file\n'
                         'Please refer to the documentation for configuration details')
            exit(1)

        logger.info('Configuration validation successful for selected integrations')
