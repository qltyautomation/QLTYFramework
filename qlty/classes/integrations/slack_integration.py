# Native libraries
import os
import requests
from pprint import pformat
import urllib.parse
# Third party libraries
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
# Project libraries
from qlty.utilities.utils import setup_logger
from qlty.utilities.utils import get_unique_build_id
import qlty.config as config
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class SlackIntegration:
    """
    Provides automated Slack channel messaging capabilities for test result reporting
    """

    def __init__(self):
        """
        Initialize the integration with Slack client
        """
        self.client = WebClient(token=settings.SLACK['SLACK_AUTH_TOKEN'])

    def report(self, results, run_time, testrail_run_id=None, test_run_id=None):
        """
        Publishes test results to the configured Slack channel specified in :code:`settings.py`

        :param results: Aggregated test run statistics
        :type: Dictionary
        :param run_time: Human-readable test execution duration
        :type: String
        :param testrail_run_id: Optional TestRail run ID for linking
        :type: Integer or None
        :param test_run_id: Test run identifier string
        :type: String or None
        :return: None
        """
        # Calculate test run statistics for Slack publication
        if results['failed_testcases'] > 0:
            if not config.REPORT_ON_FAIL:
                logger.warning('Failed test results detected, skipping slack notification')
                return {}
            else:
                logger.warning('Forcing slack notification despite failed results')

        self._post_results(self._create_payload(results, run_time, testrail_run_id, test_run_id))

    def _create_payload(self, results, run_time, testrail_run_id=None, test_run_id=None):
        """
        Builds JSON payload containing test run information

        :param results: Aggregated test run statistics
        :type: Dictionary
        :param run_time: Human-readable test execution duration
        :type: String
        :param testrail_run_id: Optional TestRail run ID for linking
        :type: Integer or None
        :param test_run_id: Test run identifier string
        :type: String or None
        :return: None
        """
        # Slack stopped supporting tabs "\t" in messages
        spaces = '   '
        # Build results summary text
        results_summary = ":bar_chart:{}*{}*{}:white_check_mark:{}*{}* ({})".format(
            spaces, results['total_testcases'], spaces, spaces,
            results['passed_testcases'], results['passed_percentage'])

        # Include failed test count if applicable
        if results['failed_testcases'] > 0:
            results_summary += '{}:x:{}*{}* ({})'.format(spaces, spaces, results['failed_testcases'],
                                                               results['failed_percentage'])

        # Build title using test_run_id if available, otherwise use BUILD_ID
        if test_run_id:
            title_text = test_run_id
        else:
            from qlty.utilities.utils import BUILD_ID
            title_text = BUILD_ID

        # Build initial payload structure
        payload = {
            # "channel": settings.SLACK['CHANNEL'],
            "blocks": []
        }

        # Add header - with TestRail link if available, otherwise plain text
        if testrail_run_id and hasattr(settings, 'TESTRAIL'):
            testrail_url = "{}/index.php?/runs/view/{}".format(
                settings.TESTRAIL['BASE_URL'].rstrip('/'),
                testrail_run_id
            )
            # Split title to make only BUILD_ID and PROJECT clickable
            # Format: "{BUILD_ID} {PROJECT} running on {PLATFORM} | started at [{TIME}] by {USER}"
            if ' running on ' in title_text:
                link_part, rest_part = title_text.split(' running on ', 1)
                formatted_text = "*<{}|{}>* running on {}".format(testrail_url, link_part, rest_part)
            else:
                formatted_text = "*<{}|{}>*".format(testrail_url, title_text)

            payload['blocks'].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": formatted_text
                }
            })
        else:
            payload['blocks'].append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title_text
                }
            })

        # Add context section with platform, release, environment, and run time
        payload['blocks'].append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Platform:\t{}".format(config.CURRENT_PLATFORM.upper())
                },
                {
                    "type": "mrkdwn",
                    "text": "Release:\t{}".format(settings.PROJECT_CONFIG['RELEASE'])
                },
                {
                    "type": "mrkdwn",
                    "text": "Environment:\t{}".format(self._get_environment_url())
                },
                {
                    "type": "mrkdwn",
                    "text": "Run time:\t{}".format(run_time)
                }
            ]
        })
        payload['blocks'].append({
            "type": "divider"
        })
        payload['blocks'].append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": results_summary
                }
            ]
        })
        # Include action buttons
        actions = self._get_button_blocks()
        # Append blocks if integrations are available
        if actions:
            payload['blocks'].append(actions)

        # Build payload footer
        payload['blocks'].append(
            {
                "type": "divider"
            })
        payload['blocks'].append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":rocket: Powered by *QLTY Framework* | v 1.0.0"
                    }
                ]
            })

        return payload

    def _get_button_blocks(self):
        """
        Generates action button blocks for Slack message based on
        active integration configurations

        :return: JSON payload with integration action buttons
        :rtype: Dictionary
        """
        actions = {
            'type': 'actions',
            'elements': []
        }

        # Include Saucelabs button if running on saucelabs
        if config.SAUCELABS_INTEGRATION:
            actions['elements'].append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Saucelabs",
                    },
                    "url": "https://app.saucelabs.com/dashboard/tests/rdc",
                    "action_id": "qlty-saucelabs"
                }
            )
        # Include Jenkins button if running on jenkins
        if config.RUNNING_ON_JENKINS:
            # Build complete jenkins URL for current platform
            jenkins_url = '{}{}{}'.format(config.JENKINS['INDUSTRIES_URL'], config.JENKINS['QLTY_JOBS_URL'],
                                          os.getenv('BUILD_NUMBER')).replace(
                '{CURRENT_PLATFORM}', settings.JENKINS['JOBS'][config.CURRENT_PLATFORM])

            actions['elements'].append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Jenkins",
                    },
                    "url": jenkins_url,
                    "action_id": "qlty-jenkins"
                }
            )

        # Only return payload if buttons were added
        if len(actions['elements']) > 0:
            return actions

    def _get_environment_url(self):
        """
        Returns the BASE URL for the current environment

        :return: BASE URL string or environment name as fallback
        :rtype: String
        """
        # Try to get BASE_URL from PROJECT_CONFIG directly
        if 'BASE_URL' in settings.PROJECT_CONFIG:
            return settings.PROJECT_CONFIG['BASE_URL']

        # Try to get BASE_URL from ENVIRONMENTS dictionary
        environment = settings.PROJECT_CONFIG.get('ENVIRONMENT')
        if hasattr(settings, 'ENVIRONMENTS') and environment in settings.ENVIRONMENTS:
            if 'BASE_URL' in settings.ENVIRONMENTS[environment]:
                return settings.ENVIRONMENTS[environment]['BASE_URL']

        # Fall back to environment name for backward compatibility
        return environment if environment else 'Unknown'

    def _get_platform_emoji(self):
        """
        Returns the appropriate emoji representing the current platform configuration

        :return: Platform emoji string
        :rtype: String
        """
        if config.CURRENT_PLATFORM == 'android':
            return ':android:'
        elif config.CURRENT_PLATFORM == 'android_web':
            return ':android::globe_with_meridians:'
        elif config.CURRENT_PLATFORM == 'ios':
            return ':apple:'
        elif config.CURRENT_PLATFORM == 'ios_web':
            return ':apple::globe_with_meridians:'
        elif config.CURRENT_PLATFORM == 'chrome':
            return ':desktop_computer::globe_with_meridians:'
        elif config.CURRENT_PLATFORM == 'firefox':
            return ':desktop_computer::fire:'
        else:
            logger.warning('No icon defined for platform: {}'.format(config.CURRENT_PLATFORM))
            return ':computer:'

    def _post_results(self, payload):
        """
        Publishes message to Slack using REST API endpoint for the configured channel

        :param payload: Data formatted in Slack block kit structure
        """
        try:
            result = self.client.chat_postMessage(
                channel=settings.SLACK['CHANNEL_ID'],
                blocks=payload['blocks'],
                icon_emoji=':astro-love:'
            )
            logger.info(result)
        except SlackApiError as e:
            logger.info('Slack notification failed\nError: {}'.format(e))
