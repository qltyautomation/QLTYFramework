# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class Integration:
    """
    Base class for lifecycle integrations.
    Subclasses override only the hooks they need — all hooks are no-ops by default.
    """

    #: When True, a failed on_run_start() aborts the entire test run
    #: instead of just deregistering the integration.
    required = False

    def on_run_start(self):
        """Called before test execution begins. Override if needed."""
        pass

    def on_test_end(self, test_case, result):
        """
        Called after each test completes. Override if needed.

        :param test_case: The test case instance that just finished
        :param result: The test result dict
        """
        pass

    def on_run_end(self, test_results, test_run_id, elapsed_time, log_path=None, context=None):
        """
        Called after all tests complete. Override if needed.

        :param test_results: Collection of test execution results
        :type test_results: dict
        :param test_run_id: Unique test run identifier
        :type test_run_id: str
        :param elapsed_time: Total test run duration in seconds
        :type elapsed_time: float
        :param log_path: Path to the captured console output log file
        :type log_path: str or None
        :param context: Shared context dict for passing data between integrations
        :type context: dict or None
        """
        pass
