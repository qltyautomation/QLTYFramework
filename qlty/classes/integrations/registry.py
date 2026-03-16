# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)

# Active integration instances
_integrations = []


def register(integration):
    """
    Register an integration instance for lifecycle dispatch.

    :param integration: An Integration subclass instance
    :type integration: Integration
    """
    _integrations.append(integration)
    logger.debug('Registered integration: {}'.format(integration.__class__.__name__))


def get_integrations():
    """
    Returns a copy of the registered integrations list.

    :return: List of registered integration instances
    :rtype: list
    """
    return list(_integrations)


def clear():
    """Removes all registered integrations."""
    _integrations.clear()


def on_run_start():
    """
    Calls on_run_start() on all registered integrations.
    Integrations that fail validation are deregistered so their
    subsequent lifecycle hooks are not called.
    """
    failed = []
    for integration in _integrations:
        try:
            integration.on_run_start()
        except Exception as e:
            logger.warning('{} failed startup validation and will be disabled: {}'.format(
                integration.__class__.__name__, e))
            failed.append(integration)

    for integration in failed:
        _integrations.remove(integration)


def on_test_end(test_case, result):
    """
    Calls on_test_end() on all registered integrations.

    :param test_case: The test case instance that just finished
    :param result: The test result dict
    """
    for integration in _integrations:
        try:
            integration.on_test_end(test_case, result)
        except Exception as e:
            logger.warning('{} on_test_end failed: {}'.format(
                integration.__class__.__name__, e))


def on_run_end(test_results, test_run_id, elapsed_time, log_path=None):
    """
    Calls on_run_end() on all registered integrations with a shared context dict.
    Each integration can read from and write to context to share data.

    :param test_results: Collection of test execution results
    :type test_results: dict
    :param test_run_id: Unique test run identifier
    :type test_run_id: str
    :param elapsed_time: Total test run duration in seconds
    :type elapsed_time: float
    :param log_path: Path to the captured console output log file
    :type log_path: str or None
    """
    context = {}
    for integration in _integrations:
        try:
            integration.on_run_end(test_results, test_run_id, elapsed_time, log_path, context)
        except Exception as e:
            logger.warning('{} on_run_end failed: {}'.format(
                integration.__class__.__name__, e))
