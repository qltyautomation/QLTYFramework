# Native libraries
import re
import html
import time
# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class EmailIntegration:
    """
    Base class for email integrations (Mailtrap, mail.tm, etc.).
    Provides shared polling and link extraction logic.
    Subclasses must implement _fetch_messages() and _get_message_body().
    """

    def _fetch_messages(self):
        """
        Fetch messages from the inbox. Subclasses must implement this.

        :return: List of message summaries
        :rtype: list
        """
        raise NotImplementedError

    def _filter_messages(self, messages, recipient_email=None):
        """
        Filter messages by recipient. Override if the provider requires filtering.
        Default returns all messages (e.g. mail.tm inboxes are per-account).

        :param messages: List of message summaries
        :param recipient_email: Optional recipient to filter by
        :return: Filtered list of messages
        :rtype: list
        """
        return messages

    def _get_message_body(self, message_id):
        """
        Retrieve the full message content and return normalized body.
        Subclasses must implement this and return a dict with 'html' and 'text' string keys.

        :param message_id: The message ID
        :type message_id: str or int
        :return: Dict with 'html' (str) and 'text' (str) keys
        :rtype: dict
        """
        raise NotImplementedError

    def poll_for_verification_link(self, max_wait=60, poll_interval=6, url_prefix=None, recipient_email=None):
        """
        Polls for a verification email and extracts the confirmation link.

        :param max_wait: Maximum time to wait for email in seconds
        :type max_wait: int
        :param poll_interval: Time between polling attempts in seconds
        :type poll_interval: int
        :param url_prefix: Optional URL prefix to search for
        :type url_prefix: str or None
        :param recipient_email: Optional recipient email to filter by (used by Mailtrap)
        :type recipient_email: str or None
        :return: The verification link URL
        :rtype: str
        :raises Exception: If no email is found or verification link cannot be extracted
        """
        target = recipient_email or getattr(self, 'email', 'unknown')
        logger.info('Polling for verification email to: {} (max_wait={}s, poll_interval={}s)'.format(
            target, max_wait, poll_interval
        ))

        start_time = time.time()
        message = None
        attempt = 0

        while (time.time() - start_time) < max_wait:
            attempt += 1
            elapsed = round(time.time() - start_time, 1)

            try:
                messages = self._fetch_messages()
                messages = self._filter_messages(messages, recipient_email)
            except Exception as e:
                logger.warning('Attempt {} ({}s): Error polling messages: {}'.format(attempt, elapsed, e))
                time.sleep(poll_interval)
                continue

            if messages:
                message = messages[0]
                logger.info('Attempt {} ({}s): Email received — subject: {}, from: {}'.format(
                    attempt, elapsed,
                    message.get('subject', 'N/A'),
                    message.get('from', {}).get('address', message.get('from_email', 'N/A'))
                ))
                break

            logger.info('Attempt {} ({}s): No email yet for {}'.format(attempt, elapsed, target))
            time.sleep(poll_interval)

        if not message:
            elapsed = round(time.time() - start_time, 1)
            raise Exception(
                'No email found for {} after {} attempts over {}s '
                '(max_wait={}s, poll_interval={}s)'.format(target, attempt, elapsed, max_wait, poll_interval)
            )

        message_id = message.get('id')
        body = self._get_message_body(message_id)

        verification_link = self._extract_verification_link(body['html'], body['text'], url_prefix)

        if not verification_link:
            body_preview = (body.get('text', '') or '')[:500]
            raise Exception(
                'Could not extract verification link from email {}. '
                'url_prefix={!r}, body preview: {}'.format(message_id, url_prefix, body_preview)
            )

        logger.info('Verification link found: {}'.format(verification_link))
        return verification_link

    @staticmethod
    def _extract_verification_link(html_body, text_body, url_prefix=None):
        """
        Extracts a verification/confirmation link from email body content.

        :param html_body: HTML body of the email
        :type html_body: str
        :param text_body: Plain text body of the email
        :type text_body: str
        :param url_prefix: Optional URL prefix to search for
        :type url_prefix: str or None
        :return: The verification link URL, or None if not found
        :rtype: str or None
        """
        if url_prefix:
            escaped_prefix = re.escape(url_prefix)
            prefix_pattern = escaped_prefix + r'[^\s<>"\']*'

            for body in [html_body, text_body]:
                match = re.search(prefix_pattern, body)
                if match:
                    link = match.group(0).rstrip('",;\'')
                    link = html.unescape(link)
                    logger.info('Found verification link with prefix: {}'.format(link))
                    return link

            logger.warning('Could not find link with prefix: {}'.format(url_prefix))
            return None

        patterns = [
            r'https?://[^\s<>"\']+(?:verify|confirm|activate|token)[^\s<>"\']*',
            r'href=["\']([^"\']*(?:verify|confirm|activate|token)[^"\']*)["\']',
        ]

        for pattern in patterns:
            for body in [html_body, text_body]:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    link = match.group(1) if match.lastindex else match.group(0)
                    link = link.replace('href=', '').replace('"', '').replace("'", '')
                    link = html.unescape(link)
                    return link

        logger.warning('Could not find verification link using standard patterns')
        return None
