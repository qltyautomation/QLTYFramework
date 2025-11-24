# Native libraries
import requests
import base64
# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class TestRailIntegration:
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

        # Test connection on initialization
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
