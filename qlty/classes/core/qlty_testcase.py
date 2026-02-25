# Native libraries
import unittest
# Third party libraries
# Project libraries
from qlty.utilities.selenium_utils import initialize_driver
from qlty.qlty_tests import test_reporter
from qlty.utilities.utils import setup_logger, dump_test_results, dump_logs, dump_screenshot
from qlty.classes.integrations.saucelabs_integration import SaucelabsHelper
import settings
import qlty.config as config

# Configure logging instance
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class QLTYTestCase(unittest.TestCase):
    """
    Base test case class for QLTY test implementations
    Extends unittest.TestCase with framework-specific functionality
    """
    #: Collection of webdriver instances for application interaction
    drivers = []
    #: Flag to enable/disable log collection during tearDown
    collect_logs = True

    def setUp(self):
        """
        Initializes webdriver instance for test case execution
        """
        logger.debug('Initializing new QLTY test case')
        self.drivers = []
        driver = None
        try:
            # Initialize webdriver instance
            driver = initialize_driver(self, config.CURRENT_PLATFORM, force_driver_creation=False)
        except Exception as error:
            logger.critical('Webdriver initialization failed. '
                            'Verify Appium server is running\nError:{}'.format(str(error)))
            exit(1)

    def get_driver(self):
        """
        Retrieves webdriver for page object instantiation
        Not intended for use with managed drivers feature
        """
        if config.MANAGED_DRIVERS:
            logger.error('This method should not be used with managed drivers enabled')
            exit(0)
        else:
            return self.drivers[0]

    def tearDown(self):
        """
        Terminates webdriver sessions and handles result reporting
        Reports to Saucelabs if integration is enabled
        """
        # Register results with test reporter
        test_reporter.add_test_case_result(self)
        # Generate test results directory
        if self.collect_logs:
            method_results_dir = dump_test_results(self)
            # Store results directory path for TestRail attachment uploads
            test_class = self.__class__.__qualname__
            test_method = self._testMethodName
            if test_class in test_reporter.test_results and test_method in test_reporter.test_results[test_class]:
                test_reporter.test_results[test_class][test_method]['results_dir'] = method_results_dir

        # Process each webdriver associated with test case
        for driver in self.drivers:
            if self.collect_logs:
                # Save system logs
                dump_logs(method_results_dir, driver)
                # Capture failure screenshot
                dump_screenshot(method_results_dir, self, driver)

            if config.SAUCELABS_INTEGRATION:
                # Verify if driver is Saucelabs-enabled by checking capabilities
                if 'sauce:options' in driver.caps:
                    # Terminate driver and publish results to Saucelabs
                    SaucelabsHelper.post_result(self, driver)
            # Terminate driver session
            driver.quit()
