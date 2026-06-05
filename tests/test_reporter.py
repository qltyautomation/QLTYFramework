import unittest

from qlty.classes.core.test_reporter import TestReporter
from qlty.classes.core.test_target import TestTarget


class SampleTestCase:
    """
    Minimal stand-in for a unittest TestCase. TestReporter only reads
    ``__class__.__qualname__`` and ``_testMethodName`` off the test case, so we
    don't need a real TestCase (which would drag in driver/fixture wiring).
    """

    def __init__(self, method_name):
        self._testMethodName = method_name


class _ErrorHolder:
    """
    Mirrors unittest's _ErrorHolder, used for module/class-level failures
    (setUpClass / setUpModule / cleanup). Its qualname is what TestReporter
    keys on, so the class name here must stay '_ErrorHolder'.
    """

    def __init__(self, description):
        self.description = description


class GetFailedResultsTests(unittest.TestCase):
    """
    Unit tests for TestReporter._get_failed_results — the step that annotates
    test_results with failure status/stack traces at run completion.

    test_results / external_case_ids are class-level on TestReporter, so each
    test shadows them with fresh instance dicts to avoid cross-test bleed.
    """

    def setUp(self):
        self.reporter = TestReporter()
        self.reporter.test_results = {}
        self.reporter.external_case_ids = {}

    def _register(self, test_case, case_ids):
        """Simulate a test that reached its register_test_case call."""
        self.reporter.register_test_case(
            test_case=test_case,
            case_ids=case_ids,
            feature_name='Sample Feature',
            test_target=TestTarget.UI,
        )

    def test_marks_registered_test_as_failed(self):
        tc = SampleTestCase('test_something')
        self._register(tc, [101])

        self.reporter._get_failed_results([(tc, 'the stack trace')])

        entry = self.reporter.test_results['SampleTestCase']['test_something']
        self.assertEqual(entry['status'], 'failed')
        self.assertEqual(entry['message'], 'the stack trace')

    def test_setup_failure_before_registration_does_not_raise(self):
        # Regression: a test that errors in setUp never calls register_test_case,
        # so it has no test_results entry. _get_failed_results must not KeyError —
        # previously this aborted reporting entirely (and Slack/TestRail never sent).
        tc = SampleTestCase('test_never_registered')

        self.reporter._get_failed_results([(tc, 'setup blew up')])

        entry = self.reporter.test_results['SampleTestCase']['test_never_registered']
        self.assertEqual(entry['status'], 'failed')
        self.assertEqual(entry['message'], 'setup blew up')
        # Synthesized entries carry no external case IDs.
        self.assertEqual(entry['test_case_ids'], [])

    def test_error_holder_does_not_abort_remaining_results(self):
        # A module/class-level _ErrorHolder must be logged and skipped, not halt
        # processing of the real failures that follow it in the list.
        holder = _ErrorHolder('setUpClass (tests.SomeClass)')
        tc = SampleTestCase('test_after_holder')
        self._register(tc, [202])

        self.reporter._get_failed_results([
            (holder, 'holder trace'),
            (tc, 'real failure trace'),
        ])

        entry = self.reporter.test_results['SampleTestCase']['test_after_holder']
        self.assertEqual(entry['status'], 'failed')
        self.assertEqual(entry['message'], 'real failure trace')


if __name__ == "__main__":
    unittest.main()
