# Native libraries
import requests
import re
import html
import time
import uuid
# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class MailTMIntegration:
    """
    Provides disposable email capabilities for test automation using mail.tm.
    No API key or configuration required. Creates temporary email accounts
    and retrieves messages sent to them — useful for verifying registration flows
    in production environments where Mailtrap cannot be used.

    Usage:
        mail = MailTMIntegration()
        email = mail.email  # e.g., 'a1b2c3d4e5@dollicons.com'

        # ... use email in registration form ...

        link = mail.get_verification_link(max_wait=60, url_prefix='https://example.com/verify/')
        driver.get(link)
    """

    BASE_URL = "https://api.mail.tm"

    def __init__(self):
        """
        Initialize the mail.tm integration by creating a disposable email account.
        Fetches available domains, creates an account, and authenticates automatically.
        """
        self._domain = self._get_domain()
        login = f"qlty.{uuid.uuid4().hex[:6]}"
        self._password = uuid.uuid4().hex
        self.email = f"{login}@{self._domain}"

        self._create_account()
        self._token = self._authenticate()

        logger.info(f"MailTMIntegration ready with email: {self.email}")

    def get_emails(self):
        """
        Retrieves all emails in the inbox.

        :return: List of message summaries
        :rtype: list
        """
        messages = self._get_messages()
        logger.info(f"Found {len(messages)} emails for {self.email}")
        return messages

    def get_verification_link(self, max_wait=30, poll_interval=2, url_prefix=None):
        """
        Polls for a verification email and extracts the confirmation link.

        :param max_wait: Maximum time to wait for email in seconds (default: 30)
        :type max_wait: int
        :param poll_interval: Time between polling attempts in seconds (default: 2)
        :type poll_interval: int
        :param url_prefix: Optional URL prefix to search for (e.g., 'https://example.com/verify/')
        :type url_prefix: str or None
        :return: The verification link URL extracted from the email
        :rtype: str
        :raises Exception: If no email is found or verification link cannot be extracted
        """
        logger.info(f"Waiting for verification email to: {self.email}")

        start_time = time.time()
        message = None

        while (time.time() - start_time) < max_wait:
            messages = self._get_messages()

            if messages:
                message = messages[0]
                logger.info(f"Found email with subject: {message.get('subject', 'N/A')}")
                break

            logger.debug(f"No email found yet, waiting {poll_interval} seconds...")
            time.sleep(poll_interval)

        if not message:
            raise Exception(f"No email found for {self.email} after {max_wait} seconds")

        full_message = self._get_message_content(message['id'])

        verification_link = self._extract_verification_link(full_message, url_prefix=url_prefix)

        if not verification_link:
            raise Exception(f"Could not extract verification link from email {message['id']}")

        logger.info(f"Verification link found: {verification_link}")
        return verification_link

    def _get_domain(self):
        """
        Fetches available domains from mail.tm and returns the first active one.

        :return: An active domain string
        :rtype: str
        """
        try:
            response = requests.get(f"{self.BASE_URL}/domains")
            response.raise_for_status()
            data = response.json()
            members = data.get('hydra:member', [])
            if not members:
                raise Exception("No domains available from mail.tm")
            domain = members[0]['domain']
            logger.debug(f"Using mail.tm domain: {domain}")
            return domain
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve domains from mail.tm: {e}")
            raise

    def _create_account(self):
        """
        Creates a new disposable email account on mail.tm.
        Updates self.email to the canonical address returned by the API
        (mail.tm may normalize the address, e.g. stripping periods).
        """
        try:
            response = requests.post(f"{self.BASE_URL}/accounts", json={
                'address': self.email,
                'password': self._password
            })
            response.raise_for_status()
            self.email = response.json()['address']
            logger.debug(f"Created mail.tm account: {self.email}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create mail.tm account: {e}")
            raise

    def _authenticate(self):
        """
        Authenticates with mail.tm and returns a JWT token.

        :return: JWT bearer token
        :rtype: str
        """
        try:
            response = requests.post(f"{self.BASE_URL}/token", json={
                'address': self.email,
                'password': self._password
            })
            response.raise_for_status()
            token = response.json()['token']
            logger.debug("Authenticated with mail.tm")
            return token
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with mail.tm: {e}")
            raise

    def _get_auth_headers(self):
        """
        Returns authorization headers for authenticated API calls.

        :return: Headers dict with Bearer token
        :rtype: dict
        """
        return {'Authorization': f'Bearer {self._token}'}

    def _get_messages(self):
        """
        Retrieves messages from the inbox.

        :return: List of message summaries
        :rtype: list
        """
        try:
            response = requests.get(f"{self.BASE_URL}/messages", headers=self._get_auth_headers())
            response.raise_for_status()
            data = response.json()
            messages = data.get('hydra:member', [])
            logger.debug(f"Retrieved {len(messages)} messages")
            return messages
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve messages: {e}")
            raise

    def _get_message_content(self, message_id):
        """
        Retrieves the full content of a specific message.

        :param message_id: The message ID
        :type message_id: str
        :return: Full message content
        :rtype: dict
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/messages/{message_id}",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            message = response.json()
            logger.debug(f"Retrieved message {message_id}")
            return message
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            raise

    def _extract_verification_link(self, message, url_prefix=None):
        """
        Extracts the verification/confirmation link from the email body.

        :param message: The full message content from mail.tm API
        :type message: dict
        :param url_prefix: Optional URL prefix to search for
        :type url_prefix: str or None
        :return: The verification link URL, or None if not found
        :rtype: str or None
        """
        # mail.tm provides html and text in the message response
        html_body = message.get('html', [''])
        # html field is a list of strings
        if isinstance(html_body, list):
            html_body = ''.join(html_body)
        text_body = message.get('text', '')

        if url_prefix:
            escaped_prefix = re.escape(url_prefix)
            prefix_pattern = escaped_prefix + r'[^\s<>"\']*'

            match = re.search(prefix_pattern, html_body)
            if match:
                link = match.group(0).rstrip('",;\'')
                link = html.unescape(link)
                logger.info(f"Found verification link with prefix: {link}")
                return link

            match = re.search(prefix_pattern, text_body)
            if match:
                link = match.group(0).rstrip('",;\'')
                link = html.unescape(link)
                logger.info(f"Found verification link with prefix: {link}")
                return link

            logger.warning(f"Could not find link with prefix: {url_prefix}")
            return None

        patterns = [
            r'https?://[^\s<>"\']+(?:verify|confirm|activate|token)[^\s<>"\']*',
            r'href=["\']([^"\']*(?:verify|confirm|activate|token)[^"\']*)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html_body, re.IGNORECASE)
            if match:
                link = match.group(1) if match.lastindex else match.group(0)
                link = link.replace('href=', '').replace('"', '').replace("'", '')
                link = html.unescape(link)
                return link

            match = re.search(pattern, text_body, re.IGNORECASE)
            if match:
                link = match.group(1) if match.lastindex else match.group(0)
                link = link.replace('href=', '').replace('"', '').replace("'", '')
                link = html.unescape(link)
                return link

        logger.warning("Could not find verification link using standard patterns")
        return None
