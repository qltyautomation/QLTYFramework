# Native libraries
import os
import pwd
import requests
import base64
# Project libraries
from qlty.classes.integrations.base_integration import Integration
from qlty.utilities.utils import setup_logger
import qlty.config as config
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class TestRailIntegration(Integration):
    """
    Provides TestRail API integration for test result reporting.
    Enables creation of test runs and submission of test results to TestRail.
    """

    def __init__(self):
        """
        Initialize the TestRail integration with API credentials from settings
        """
        self.base_url = settings.TESTRAIL['BASE_URL'].rstrip('/')
        self.username = settings.TESTRAIL['USERNAME']
        self.api_key = settings.TESTRAIL['API_KEY']
        self.project_id = settings.TESTRAIL['PROJECT_ID']
        self.suite_id = settings.TESTRAIL['SUITE_ID']

        # Setup authentication
        auth_string = f"{self.username}:{self.api_key}"
        auth_bytes = auth_string.encode('ascii')
        base64_bytes = base64.b64encode(auth_bytes)
        base64_string = base64_bytes.decode('ascii')

        self.headers = {
            'Authorization': f'Basic {base64_string}',
            'Content-Type': 'application/json'
        }

    def on_run_start(self):
        """Validates TestRail connection and credentials before tests run."""
        self._test_connection()

    def _test_connection(self):
        """
        Tests the connection to TestRail API by making a simple GET request

        :raises Exception: If connection fails or credentials are invalid
        """
        url = f"{self.base_url}/index.php?/api/v2/get_projects"

        try:
            logger.info("Testing connection to TestRail API...")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            projects = response.json()
            logger.info(f"Successfully connected to TestRail. Found {len(projects)} projects.")

            # Verify the project exists
            if isinstance(projects, list):
                project_found = False
                for project in projects:
                    if isinstance(project, dict) and str(project.get('id')) == str(self.project_id):
                        project_found = True
                        logger.info(f"Project found: {project.get('name')} (ID: {project.get('id')})")
                        break

                if not project_found:
                    logger.warning(f"Project ID {self.project_id} not found in available projects")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to TestRail API: {e}")
            raise

    def create_test_run(self, name, description=None, case_ids=None):
        """
        Creates a new test run in TestRail with specific test cases or all cases from the suite.

        :param name: Name of the test run
        :type name: str
        :param description: Description of the test run (optional)
        :type description: str
        :param case_ids: List of specific test case IDs to include in the run (optional)
        :type case_ids: list[int]
        :return: The created test run object containing run_id
        :rtype: dict
        :raises Exception: If test run creation fails
        """
        url = f"{self.base_url}/index.php?/api/v2/add_run/{self.project_id}"

        payload = {
            'name': name,
            'suite_id': self.suite_id
        }

        # If specific case IDs provided, include only those; otherwise include all
        if case_ids:
            payload['include_all'] = False
            payload['case_ids'] = case_ids
            logger.debug(f"Creating run with {len(case_ids)} specific test cases")
        else:
            payload['include_all'] = True
            logger.debug("Creating run with all test cases from suite")

        if description:
            payload['description'] = description

        try:
            logger.info(f"Creating TestRail test run: {name}")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            test_run = response.json()
            logger.info(f"Test run created successfully with ID: {test_run['id']}")
            logger.info(f"View run at: {self.base_url}/index.php?/runs/view/{test_run['id']}")
            return test_run
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create test run in TestRail: {e}")
            raise

    def add_result_for_case(self, run_id, case_id, status, comment=None, elapsed=None):
        """
        Adds a test result for a specific test case in a test run.
        This method should be called at the end of each test case execution.

        :param run_id: The ID of the test run
        :type run_id: int
        :param case_id: The ID of the test case (e.g., 69 for case C69)
        :type case_id: int
        :param status: The status of the test (passed, failed, blocked, retest, untested)
        :type status: str
        :param comment: Comment or error message for the result (optional)
        :type comment: str
        :param elapsed: Time elapsed in seconds or time string (e.g., "1m 30s") (optional)
        :type elapsed: str
        :return: The created test result object
        :rtype: dict
        :raises Exception: If adding result fails

        Status values:
        - 'passed' or 1: Test passed
        - 'blocked' or 2: Test blocked
        - 'untested' or 3: Test not executed
        - 'retest' or 4: Test needs retest
        - 'failed' or 5: Test failed
        """
        url = f"{self.base_url}/index.php?/api/v2/add_result_for_case/{run_id}/{case_id}"

        # Convert status to status_id if it's a string
        if isinstance(status, str):
            status_map = {
                'passed': 1,
                'blocked': 2,
                'untested': 3,
                'retest': 4,
                'failed': 5
            }
            status_id = status_map.get(status.lower(), 3)
        else:
            status_id = status

        payload = {
            'status_id': status_id
        }

        if comment:
            payload['comment'] = comment

        if elapsed:
            payload['elapsed'] = elapsed

        try:
            logger.debug(f"Adding result for case {case_id} in run {run_id}: status={status}")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Result added successfully for case {case_id} - Status: {status}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add result for case {case_id}: {e}")
            raise

    def update_run(self, run_id, case_ids):
        """
        Updates a test run to include only specific test cases.
        This is useful for removing untested cases from the run after execution completes.

        :param run_id: The ID of the test run to update
        :type run_id: int
        :param case_ids: List of test case IDs to include in the run
        :type case_ids: list
        :return: The updated test run object
        :rtype: dict
        :raises Exception: If update fails
        """
        url = f"{self.base_url}/index.php?/api/v2/update_run/{run_id}"

        payload = {
            'case_ids': case_ids
        }

        try:
            logger.info(f"Updating test run {run_id} to include {len(case_ids)} test cases")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            test_run = response.json()
            logger.info(f"Test run {run_id} updated successfully - untested cases removed")
            return test_run
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update test run {run_id}: {e}")
            raise

    @staticmethod
    def resolve_case_ids(case_map, config):
        """
        Resolve which TestRail case IDs apply based on a case map and a configuration object.
        Filters out None values and evaluates conditional entries against config flags.

        :param case_map: Dictionary with 'core' (always-included cases) and
                         conditional entries keyed by field name. Each conditional entry has:
                         - 'case_id': int or None
                         - 'config_key': str (flag name to check on config)
                         - 'inverted': bool (optional, include when config value is falsy)
                         - 'config_list': str (optional, include when config list is non-empty)
        :type case_map: dict
        :param config: Object with a get_value(key, default=None) method
        :return: List of applicable TestRail case IDs
        :rtype: list[int]
        """
        case_ids = []

        # Core fields (always included)
        for case_id in case_map['core'].values():
            if case_id is not None:
                case_ids.append(case_id)

        # Conditional fields
        for key, mapping in case_map.items():
            if key == 'core':
                continue

            case_id = mapping.get('case_id')
            if case_id is None:
                continue

            # List-based: include if the config list is non-empty
            if 'config_list' in mapping:
                config_list = config.get_value(mapping['config_list'], [])
                if config_list:
                    case_ids.append(case_id)
                continue

            # Flag-based: check config key
            config_key = mapping.get('config_key', '')
            inverted = mapping.get('inverted', False)

            if inverted:
                raw_value = config.get_value(config_key, False)
                if not raw_value:
                    case_ids.append(case_id)
            else:
                raw_value = config.get_value(config_key)
                if raw_value:
                    case_ids.append(case_id)

        return case_ids

    def add_attachment_to_run(self, run_id, file_path):
        """
        Attaches a file to a test run in TestRail.

        :param run_id: The ID of the test run
        :type run_id: int
        :param file_path: Absolute path to the file to attach
        :type file_path: str
        :return: The attachment response object
        :rtype: dict
        :raises Exception: If attachment upload fails
        """
        url = f"{self.base_url}/index.php?/api/v2/add_attachment_to_run/{run_id}"

        upload_headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    url,
                    headers=upload_headers,
                    files={'attachment': (filename, f)}
                )
            response.raise_for_status()
            logger.info(f"Attached '{filename}' to run {run_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to attach '{filename}' to run {run_id}: {e}")
            raise

    def add_attachment_to_result(self, result_id, file_path):
        """
        Attaches a file to a specific test result in TestRail.
        Supports screenshots, logs, and other artifacts for debugging.

        :param result_id: The ID of the test result (returned by add_result_for_case)
        :type result_id: int
        :param file_path: Absolute path to the file to attach
        :type file_path: str
        :return: The attachment response object
        :rtype: dict
        :raises Exception: If attachment upload fails
        """
        url = f"{self.base_url}/index.php?/api/v2/add_attachment_to_result/{result_id}"

        # Multipart uploads require removing Content-Type header
        # so requests can set the correct multipart boundary automatically
        upload_headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}

        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    url,
                    headers=upload_headers,
                    files={'attachment': (filename, f)}
                )
            response.raise_for_status()
            logger.debug(f"Attachment '{filename}' uploaded to result {result_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to attach '{filename}' to result {result_id}: {e}")
            raise

    def on_run_end(self, test_results, test_run_id, elapsed_time, log_path=None, context=None):
        """
        Lifecycle hook called after all tests complete.
        Creates a TestRail run, submits results, attaches artifacts and console log.
        Sets context['testrail_run_id'] for downstream integrations.

        :param test_results: Collection of test execution results
        :param test_run_id: Unique test run identifier
        :param elapsed_time: Total test run duration in seconds
        :param log_path: Path to the captured console output log file
        :param context: Shared context dict for passing data between integrations
        """
        from qlty.classes.core.test_runner_utils import TestRunnerUtils

        # Check for failures and respect REPORT_ON_FAIL setting
        totals = TestRunnerUtils.get_testrun_totals(test_results)
        if totals['failed_testcases'] > 0:
            if not config.REPORT_ON_FAIL:
                logger.warning('Failed test results detected, skipping TestRail reporting')
                return
            else:
                logger.warning('Forcing TestRail reporting despite failed results')

        # Collect all case IDs across all test results
        all_case_ids = []
        for test_class, test_methods in test_results.items():
            for test_method, result in test_methods.items():
                if result.get('test_case_ids') and len(result['test_case_ids']) > 0:
                    all_case_ids.extend(result['test_case_ids'])

        # Deduplicate while preserving order
        all_case_ids = list(dict.fromkeys(all_case_ids))

        if not all_case_ids:
            logger.warning('No test cases with TestRail IDs found, skipping reporting')
            return

        logger.debug('{} case(s) to report: {}'.format(len(all_case_ids), all_case_ids))

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
            TestRunnerUtils.get_readable_run_time(elapsed_time)))
        description_lines.append('Executed by: {}'.format(executed_by))
        if config.HEADLESS:
            description_lines.append('Mode: Headless')
        if source_repo:
            description_lines.append('Source: {}'.format(source_repo))

        run_description = '\n'.join(description_lines)

        # Create a single test run with all case IDs
        logger.info('Creating TestRail run with {} case(s)'.format(len(all_case_ids)))
        test_run = self.create_test_run(test_run_id, run_description, case_ids=all_case_ids)
        run_id = test_run['id']

        # Share run ID with other integrations via context
        if context is not None:
            context['testrail_run_id'] = run_id

        # Submit results for each test case
        for test_class, test_methods in test_results.items():
            for test_method, result in test_methods.items():
                if not result.get('test_case_ids') or len(result['test_case_ids']) == 0:
                    continue

                first_result_id = None
                first_test_id = None
                for case_id in result['test_case_ids']:
                    try:
                        status = result['status']
                        comment = result.get('message', '')
                        elapsed = TestRunnerUtils.get_readable_run_time(result['duration']) if result.get('duration') else None

                        test_identifier = '{}.{}'.format(test_class, test_method)
                        if comment:
                            comment = 'Test: {}\n\n{}'.format(test_identifier, comment)
                        else:
                            comment = 'Test: {}'.format(test_identifier)

                        # Add cross-reference to child cases pointing to the primary case with attachments
                        if first_result_id is not None and result['status'] in ('failed', 5):
                            result_url = '{}/index.php?/tests/view/{}'.format(self.base_url, first_test_id)
                            comment += '\n\n[Screenshots and logs attached here]({})'.format(result_url)

                        testrail_result = self.add_result_for_case(run_id, case_id, status, comment, elapsed)

                        # Track the first result ID and case ID for attaching artifacts once
                        if first_result_id is None:
                            first_result_id = testrail_result.get('id')
                            first_test_id = testrail_result.get('test_id')

                    except Exception as e:
                        logger.error('Failed to add result for case {}: {}'.format(case_id, str(e)))

                # Attach screenshots and logs only to failed tests
                results_dir = result.get('results_dir')
                if first_result_id and results_dir and result['status'] in ('failed', 5):
                    for filename in ['screenshot.png', 'system.log', 'page_source.txt']:
                        file_path = os.path.join(results_dir, filename)
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            try:
                                self.add_attachment_to_result(first_result_id, file_path)
                            except Exception as attach_err:
                                logger.warning('Failed to attach {} for case {}: {}'.format(
                                    filename, first_result_id, str(attach_err)))

        # Attach console output log to the TestRail run
        if log_path and os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            try:
                self.add_attachment_to_run(run_id, log_path)
            except Exception as attach_err:
                logger.warning('Failed to attach console log to run {}: {}'.format(run_id, attach_err))

        logger.info('View results at: {}/index.php?/runs/view/{}'.format(
            self.base_url, run_id))
        logger.info('TestRail reporting completed successfully')
