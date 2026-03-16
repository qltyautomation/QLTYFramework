# Native libraries
import requests
# Project libraries
from qlty.classes.integrations.email_integration import EmailIntegration
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class MailtrapIntegration(EmailIntegration):
    """
    Provides Mailtrap email access capabilities for test automation.
    Enables retrieval and parsing of test emails sent through Mailtrap.
    """

    BASE_URL = "https://mailtrap.io/api"

    def __init__(self):
        """
        Initialize the Mailtrap helper with API credentials from settings
        """
        self.api_token = settings.MAILTRAP['API_TOKEN']
        self.account_id = settings.MAILTRAP['ACCOUNT_ID']
        self.inbox_id = settings.MAILTRAP['INBOX_ID']
        self.headers = {
            'Api-Token': self.api_token,
            'Content-Type': 'application/json'
        }

    def get_emails_for_recipient(self, recipient_email, include_content=False):
        """
        Retrieves all emails sent to a specific recipient email address.

        :param recipient_email: The email address of the recipient
        :type recipient_email: str
        :param include_content: Whether to fetch full content for each email (default: False)
        :type include_content: bool
        :return: List of emails sent to the recipient
        :rtype: list
        """
        messages = self._fetch_messages()
        matching_messages = self._filter_messages(messages, recipient_email)

        logger.info(f"Found {len(matching_messages)} emails for {recipient_email}")

        if include_content and matching_messages:
            detailed_messages = []
            for msg in matching_messages:
                body = self._get_message_body(msg['id'])
                msg.update(body)
                detailed_messages.append(msg)
            return detailed_messages

        return matching_messages

    def get_verification_link(self, recipient_email, max_wait=30, poll_interval=2, url_prefix=None):
        """
        Retrieves the verification link from the latest email sent to the provided email address.

        :param recipient_email: The email address of the recipient
        :type recipient_email: str
        :param max_wait: Maximum time to wait for email in seconds (default: 30)
        :type max_wait: int
        :param poll_interval: Time between polling attempts in seconds (default: 2)
        :type poll_interval: int
        :param url_prefix: Optional URL prefix to search for
        :type url_prefix: str or None
        :return: The verification link URL extracted from the email
        :rtype: str
        :raises Exception: If no email is found or verification link cannot be extracted
        """
        return self.poll_for_verification_link(
            max_wait=max_wait,
            poll_interval=poll_interval,
            url_prefix=url_prefix,
            recipient_email=recipient_email,
        )

    def _fetch_messages(self):
        """
        Retrieves all messages from the Mailtrap inbox.

        :return: List of messages
        :rtype: list
        """
        url = f"{self.BASE_URL}/accounts/{self.account_id}/inboxes/{self.inbox_id}/messages"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            messages = response.json()
            logger.debug(f"Retrieved {len(messages)} messages from inbox")
            return messages
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve messages from Mailtrap: {e}")
            raise

    def _filter_messages(self, messages, recipient_email=None):
        """
        Filters messages by recipient email address.

        :param messages: List of message summaries
        :param recipient_email: Recipient email to filter by
        :return: Filtered list of messages
        :rtype: list
        """
        if not recipient_email:
            return messages
        return [
            msg for msg in messages
            if recipient_email in msg.get('to_email', '')
        ]

    def _get_message_body(self, message_id):
        """
        Retrieves the full content of a message and returns normalized body.

        :param message_id: The ID of the message to retrieve
        :type message_id: int
        :return: Dict with 'html' and 'text' string keys
        :rtype: dict
        """
        url = f"{self.BASE_URL}/accounts/{self.account_id}/inboxes/{self.inbox_id}/messages/{message_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            logger.debug(f"Retrieved message {message_id}")

            html_body = ''
            text_body = ''

            # Mailtrap API v2 requires separate calls for HTML and text bodies
            html_url = f"{url}/body.html"
            try:
                html_response = requests.get(html_url, headers=self.headers)
                if html_response.status_code == 200:
                    html_body = html_response.text
                    logger.debug(f"Retrieved HTML body ({len(html_body)} chars)")
            except requests.exceptions.RequestException:
                logger.warning(f"Could not retrieve HTML body for message {message_id}")

            text_url = f"{url}/body.txt"
            try:
                text_response = requests.get(text_url, headers=self.headers)
                if text_response.status_code == 200:
                    text_body = text_response.text
                    logger.debug(f"Retrieved text body ({len(text_body)} chars)")
            except requests.exceptions.RequestException:
                logger.warning(f"Could not retrieve text body for message {message_id}")

            return {
                'html': html_body,
                'text': text_body,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            raise
