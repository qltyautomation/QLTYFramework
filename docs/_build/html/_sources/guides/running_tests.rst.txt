=============================
Running tests
=============================
This section will show you how to run your tests and the available command line arguments


Test execution
==============

Run the python script :code:`test_runner.py` with the :code:`--platform=` parameter:

.. code-block:: bash

    python test_runner.py --platform=android

With this minimum setup the test runner will execute all available tests for the given platform

In order for a test to be discoverable, the test method name must have the prefix: :code:`test_`
For example: :code:`test_create_new_report`

Tests methods that do not have that prefix will not be recognized by the test runner as test methods

Configuration with local_settings.py
=====================================

.. note::

        All integrations require proper configuration in your :code:`local_settings.py` file.
        This file should be created from the :code:`local_settings.py.example` template in your test repository.
        Never commit :code:`local_settings.py` to version control as it contains sensitive credentials.

The framework uses a :code:`local_settings.py` file to manage all configuration and credentials. This approach:

- Keeps sensitive data out of version control
- Uses environment variables for CI/CD environments (Jenkins, GitHub Actions, etc.)
- Provides a consistent configuration pattern across all integrations

**Setting up local_settings.py:**

.. code-block:: bash

    # Copy the example file
    cp local_settings.py.example local_settings.py

    # Edit with your credentials
    # Add your API keys, tokens, and configuration values

The test runner validates that all required settings are present based on the flags you use. If any required configuration is missing, the framework will exit with an error message indicating which settings need to be added.


Command line arguments
======================

Test execution can be customized in many ways and integrations can also be enabled or disabled through
command line arguments. These options can be activated by the short flag or the full command name.

- **Platform** :code:`-p` or :code:`--platform` **(REQUIRED)**

    **Options:** :code:`ios`, :code:`android`, :code:`android_web`, :code:`ios_web`, :code:`chrome`, :code:`firefox`

    Defines the target platform for test execution.

    **Examples:**

    .. code-block:: bash

        # Mobile native apps
        python test_runner.py --platform=android
        python test_runner.py --platform=ios

        # Mobile web browsers
        python test_runner.py --platform=android_web
        python test_runner.py --platform=ios_web

        # Desktop browsers
        python test_runner.py --platform=chrome
        python test_runner.py --platform=firefox

    Test classes or test methods should be decorated with platform-specific decorators:

    .. code-block:: python

        @unittest.skipUnless(TestRunnerUtils.running_on_android(),
                           TestRunnerUtils.running_on_android_message)
        def test_offline_visit(self):
            # Test implementation

- **Single test** :code:`-t` or :code:`--test`

    **Default:** :code:`None` (runs all tests)

    Execute a specific test case instead of running the entire test suite.
    Multiple formats are supported:

    **Examples:**

    .. code-block:: bash

        # Run all tests in a class (simplest format)
        python test_runner.py -p chrome -t TestHomepage

        # Run a specific test method
        python test_runner.py -p chrome -t TestHomepage.test_login

        # Explicit module path (if needed)
        python test_runner.py -p chrome -t test_homepage.TestHomepage.test_login

    The framework automatically converts class names to module names (e.g., ``TestHomepage`` → ``test_homepage.TestHomepage``).

- **Slack integration** :code:`-s` or :code:`--slack`

    **Default:** :code:`False`

    Enables Slack notifications for test results. Posts test execution summaries to a configured Slack channel.

    **Required configuration in local_settings.py:**

    .. code-block:: python

        SLACK = {
            'SLACK_AUTH_TOKEN': os.getenv('SLACK_TOKEN', None),
            'CHANNEL_ID': 'C123456789',
        }

        PROJECT_CONFIG = {
            'PROJECT_NAME': 'My Project',
            'RELEASE': '1.0.0',
            'ENVIRONMENT': 'QA',
        }

    **Example:**

    .. code-block:: bash

        python test_runner.py -p android -s

- **TestRail integration** :code:`-r` or :code:`--testrail`

    **Default:** :code:`False`

    Enables TestRail integration to create test runs and report results automatically.

    **Required configuration in local_settings.py:**

    .. code-block:: python

        TESTRAIL = {
            'BASE_URL': 'https://yourcompany.testrail.io',
            'USERNAME': os.getenv('TESTRAIL_USERNAME', None),
            'API_KEY': os.getenv('TESTRAIL_API_KEY', None),
            'PROJECT_ID': 1,
            'SUITE_ID': 1,
        }

    **Example:**

    .. code-block:: bash

        python test_runner.py -p android -r

- **SauceLabs integration** :code:`-l` or :code:`--saucelabs`

    **Default:** :code:`False`

    Executes tests on SauceLabs cloud platform using virtual or real devices.

    **Required configuration in local_settings.py:**

    .. code-block:: python

        SAUCELABS = {
            'USERNAME': os.getenv('SAUCELABS_USERNAME', None),
            'ACCESS_KEY': os.getenv('SAUCELABS_ACCESS_KEY', None),
            'URL': 'https://{}:{}@ondemand.us-west-1.saucelabs.com:443/wd/hub',
        }

        # Also requires platform-specific capabilities with _saucelabs suffix
        SELENIUM = {
            'CAPABILITIES': {
                'android_saucelabs': {...},
                'ios_saucelabs': {...},
            }
        }

    **Example:**

    .. code-block:: bash

        python test_runner.py -p android -l

- **Report on fail** :code:`-f` or :code:`--report-on-fail`

    **Default:** :code:`False`

    By default, reports are only sent on successful test runs. This flag enables reporting regardless of test outcome.
    Automatically activates Slack integration.

    **Example:**

    .. code-block:: bash

        python test_runner.py -p android -s -f

    .. note::

        Without this flag, Slack reports are only sent when all tests pass. Use :code:`-f` to receive notifications
        for both passing and failing test runs.

- **Managed drivers** :code:`-d` or :code:`--managed`

    **Default:** :code:`False`

    Enables automated driver management for browser-based testing. The framework will automatically download and
    manage WebDriver binaries.

    **Example:**

    .. code-block:: bash

        python test_runner.py -p chrome -d

**Combining flags:**

Multiple flags can be combined to enable different features:

.. code-block:: bash

    # Run on Android with Slack and TestRail integrations
    python test_runner.py -p android -s -r

    # Run specific test on Chrome with Slack notifications
    python test_runner.py -p chrome -t tests.web.test_login.TestLogin.test_valid_credentials -s

    # Run on SauceLabs with all integrations and report on failure
    python test_runner.py -p ios -l -s -r -f
