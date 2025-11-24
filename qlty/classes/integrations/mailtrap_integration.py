# Native libraries
import requests
import re
import time
# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class MailtrapIntegration:
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
        messages = self._get_messages()

        # Filter messages by recipient email
        matching_messages = [
            msg for msg in messages
            if recipient_email in msg.get('to_email', '')
        ]

        logger.info(f"Found {len(matching_messages)} emails for {recipient_email}")

        # If full content is requested, fetch each message
        if include_content and matching_messages:
            detailed_messages = []
            for msg in matching_messages:
                full_msg = self._get_message_content(msg['id'])
                detailed_messages.append(full_msg)
            return detailed_messages

        return matching_messages

    def get_verification_link(self, recipient_email, max_wait=30, poll_interval=2, url_prefix=None):
        """
        Retrieves the verification link from the latest email sent to the provided email address.

        This method polls the Mailtrap inbox for a new email to the specified recipient,
        retrieves the most recent message, and extracts the verification/confirmation link
        from the email body.

        :param recipient_email: The email address of the recipient
        :type recipient_email: str
        :param max_wait: Maximum time to wait for email in seconds (default: 30)
        :type max_wait: int
        :param poll_interval: Time between polling attempts in seconds (default: 2)
        :type poll_interval: int
        :param url_prefix: Optional URL prefix to search for (e.g., "https://example.com/verify/")
        :type url_prefix: str or None
        :return: The verification link URL extracted from the email
        :rtype: str
        :raises Exception: If no email is found or verification link cannot be extracted
        """
        logger.info(f"Waiting for verification email to: {recipient_email}")

        # Poll for the email
        start_time = time.time()
        message = None

        while (time.time() - start_time) < max_wait:
            messages = self._get_messages()

            # Filter messages by recipient email
            matching_messages = [
                msg for msg in messages
                if recipient_email in msg.get('to_email', '')
            ]

            if matching_messages:
                # Get the latest message (first in the list, as they're sorted by date descending)
                message = matching_messages[0]
                logger.info(f"Found email with subject: {message.get('subject', 'N/A')}")
                break

            logger.debug(f"No email found yet, waiting {poll_interval} seconds...")
            time.sleep(poll_interval)

        if not message:
            raise Exception(f"No email found for {recipient_email} after {max_wait} seconds")

        # Get the full message content
        message_id = message['id']
        full_message = self._get_message_content(message_id)

        # Extract verification link from the email body
        verification_link = self._extract_verification_link(full_message, url_prefix=url_prefix)

        if not verification_link:
            raise Exception(f"Could not extract verification link from email {message_id}")

        logger.info(f"Verification link found: {verification_link}")
        return verification_link

    def _get_messages(self):
        """
        Retrieves all messages from the Mailtrap inbox

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

    def _get_message_content(self, message_id):
        """
        Retrieves the full content of a specific message including HTML and text bodies

        :param message_id: The ID of the message to retrieve
        :type message_id: int
        :return: Full message content including body
        :rtype: dict
        """
        url = f"{self.BASE_URL}/accounts/{self.account_id}/inboxes/{self.inbox_id}/messages/{message_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            message = response.json()
            logger.debug(f"Retrieved message {message_id}")

            # Mailtrap API v2 requires separate calls to get HTML and text bodies
            # Fetch HTML body
            html_url = f"{url}/body.html"
            try:
                html_response = requests.get(html_url, headers=self.headers)
                if html_response.status_code == 200:
                    message['html_body'] = html_response.text
                    logger.debug(f"Retrieved HTML body ({len(html_response.text)} chars)")
            except requests.exceptions.RequestException:
                logger.warning(f"Could not retrieve HTML body for message {message_id}")

            # Fetch text body
            text_url = f"{url}/body.txt"
            try:
                text_response = requests.get(text_url, headers=self.headers)
                if text_response.status_code == 200:
                    message['text_body'] = text_response.text
                    logger.debug(f"Retrieved text body ({len(text_response.text)} chars)")
            except requests.exceptions.RequestException:
                logger.warning(f"Could not retrieve text body for message {message_id}")

            return message
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            raise

    def _extract_verification_link(self, message, url_prefix=None):
        """
        Extracts the verification/confirmation link from the email body

        :param message: The full message content
        :type message: dict
        :param url_prefix: Optional URL prefix to search for (e.g., "https://example.com/verify/")
        :type url_prefix: str or None
        :return: The verification link URL
        :rtype: str
        """
        import html

        # Try to extract from HTML body first
        html_body = message.get('html_body', '')
        text_body = message.get('text_body', '')

        # If URL prefix is provided, search for URLs starting with that prefix
        if url_prefix:
            # Escape special regex characters in the prefix
            escaped_prefix = re.escape(url_prefix)
            # Pattern to match the prefix followed by any valid URL characters
            prefix_pattern = escaped_prefix + r'[^\s<>"\']*'

            # Try HTML body first
            match = re.search(prefix_pattern, html_body)
            if match:
                link = match.group(0)
                # Clean up trailing punctuation or HTML characters
                link = link.rstrip('",;\'')
                # Decode HTML entities (e.g., &amp; -> &)
                link = html.unescape(link)
                logger.info(f"Found verification link with prefix: {link}")
                return link

            # Try text body
            match = re.search(prefix_pattern, text_body)
            if match:
                link = match.group(0)
                link = link.rstrip('",;\'')
                # Decode HTML entities (e.g., &amp; -> &)
                link = html.unescape(link)
                logger.info(f"Found verification link with prefix: {link}")
                return link

            logger.warning(f"Could not find link with prefix: {url_prefix}")
            return None

        # Fall back to generic patterns if no prefix provided
        patterns = [
            r'https?://[^\s<>"\']+(?:verify|confirm|activate|token)[^\s<>"\']*',
            r'href=["\']([^"\']*(?:verify|confirm|activate|token)[^"\']*)["\']',
        ]

        for pattern in patterns:
            # Try HTML body first
            match = re.search(pattern, html_body, re.IGNORECASE)
            if match:
                link = match.group(1) if match.lastindex else match.group(0)
                # Clean up the link (remove href= if present)
                link = link.replace('href=', '').replace('"', '').replace("'", '')
                # Decode HTML entities (e.g., &amp; -> &)
                link = html.unescape(link)
                return link

            # Try text body
            match = re.search(pattern, text_body, re.IGNORECASE)
            if match:
                link = match.group(1) if match.lastindex else match.group(0)
                link = link.replace('href=', '').replace('"', '').replace("'", '')
                # Decode HTML entities (e.g., &amp; -> &)
                link = html.unescape(link)
                return link

        logger.warning("Could not find verification link using standard patterns")
        return None
