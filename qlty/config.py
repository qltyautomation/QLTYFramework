"""
Framework configuration settings module
Contains framework-wide parameters that apply across all test implementations
"""
# Native libraries
import os
# Import the projects settings
import settings

#: Application identifier string
PROJECT_FRIENDLY_NAME = 'QLTYMobileFramework/1.0'

#: Current execution platform identifier
CURRENT_PLATFORM = None
#: Enable Slack notification integration for test results
SLACK_REPORTING = False
#: Allow reporting functionality even when test cases fail
REPORT_ON_FAIL = False
#: Specify individual test case to execute
SINGLE_TEST_NAME = None
#: Enable SauceLabs cloud testing platform integration
SAUCELABS_INTEGRATION = False
#: Enable TestRail test management integration for result reporting
TESTRAIL_INTEGRATION = False
#: Execute tests targeting mobile web browsers
MOBILE_BROWSER = False
#: Indicates execution within Jenkins CI environment
RUNNING_ON_JENKINS = False
#: Use automated driver management for browser drivers
MANAGED_DRIVERS = False
#: Execute tests using desktop browsers via Selenium only (no Appium)
DESKTOP_BROWSER = False
#: Run browser in headless mode (no UI)
HEADLESS = False
#: Override base URL for target environment
BASE_URL = None
