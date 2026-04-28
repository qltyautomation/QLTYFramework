# Native libraries
import requests
import time
import uuid
# Project libraries
from qlty.classes.integrations.email_integration import EmailIntegration
from qlty.utilities.utils import setup_logger, get_test_email
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class MailTMIntegration(EmailIntegration):
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

    # mail.tm enforces a per-IP sliding-window rate limit on /accounts (and
    # adjacent endpoints). Across a multi-env production run we comfortably
    # exceed it late in the run, so retry with the server-supplied Retry-After.
    _RATE_LIMIT_MAX_RETRIES = 3
    _RATE_LIMIT_FALLBACK_DELAY = 30  # seconds, used when Retry-After is absent
    _RATE_LIMIT_MAX_DELAY = 360  # seconds, ceiling for any server-supplied Retry-After

    def __init__(self):
        """
        Initialize the mail.tm integration by creating a disposable email account.
        Fetches available domains, creates an account, and authenticates automatically.
        """
        self._domain = self._get_domain()
        login = get_test_email().split('@')[0]
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
        messages = self._fetch_messages()
        logger.info(f"Found {len(messages)} emails for {self.email}")
        return messages

    def get_verification_link(self, max_wait=60, poll_interval=6, url_prefix=None):
        """
        Polls for a verification email and extracts the confirmation link.

        :param max_wait: Maximum time to wait for email in seconds (default: 60)
        :type max_wait: int
        :param poll_interval: Time between polling attempts in seconds (default: 6)
        :type poll_interval: int
        :param url_prefix: Optional URL prefix to search for (e.g., 'https://example.com/verify/')
        :type url_prefix: str or None
        :return: The verification link URL extracted from the email
        :rtype: str
        :raises Exception: If no email is found or verification link cannot be extracted
        """
        return self.poll_for_verification_link(
            max_wait=max_wait,
            poll_interval=poll_interval,
            url_prefix=url_prefix,
        )

    def _fetch_messages(self):
        """
        Retrieves messages from the mail.tm inbox.

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

    def _get_message_body(self, message_id):
        """
        Retrieves the full content of a message and returns normalized body.

        :param message_id: The message ID
        :type message_id: str
        :return: Dict with 'html' and 'text' string keys
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

            # mail.tm returns html as a list of strings
            html_body = message.get('html', [''])
            if isinstance(html_body, list):
                html_body = ''.join(html_body)

            return {
                'html': html_body,
                'text': message.get('text', ''),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            raise

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
        Retries with server-supplied Retry-After on 429 responses.
        """
        try:
            response = self._post_with_rate_limit_retry(f"{self.BASE_URL}/accounts", {
                'address': self.email,
                'password': self._password
            })
            response.raise_for_status()
            self.email = response.json()['address']
            logger.debug(f"Created mail.tm account: {self.email}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create mail.tm account: {e}")
            raise

    def _post_with_rate_limit_retry(self, url, payload):
        """
        POST helper that retries on HTTP 429, honoring the Retry-After header
        when present. Falls back to a fixed delay otherwise. Non-429 errors
        and the final attempt's response are returned to the caller as-is for
        normal raise_for_status() handling.
        """
        last_response = None
        for attempt in range(self._RATE_LIMIT_MAX_RETRIES + 1):
            response = requests.post(url, json=payload)
            last_response = response
            if response.status_code != 429:
                return response

            if attempt == self._RATE_LIMIT_MAX_RETRIES:
                logger.error(f"mail.tm rate-limited after {attempt + 1} attempts on {url}")
                return response

            retry_after = response.headers.get('Retry-After')
            try:
                parsed = int(retry_after) if retry_after else self._RATE_LIMIT_FALLBACK_DELAY
            except ValueError:
                # Non-integer (e.g. an HTTP-date) — fall back rather than guess.
                parsed = self._RATE_LIMIT_FALLBACK_DELAY
            # Clamp to a sane window: floor at 0 (negative would crash time.sleep)
            # and ceiling at _RATE_LIMIT_MAX_DELAY so a misbehaving server can't
            # hang the test for hours.
            delay = max(0, min(parsed, self._RATE_LIMIT_MAX_DELAY))
            logger.warning(
                f"mail.tm 429 on {url} (attempt {attempt + 1}/"
                f"{self._RATE_LIMIT_MAX_RETRIES + 1}); sleeping {delay}s before retry"
            )
            time.sleep(delay)
        return last_response

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
