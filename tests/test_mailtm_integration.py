import unittest
from unittest.mock import MagicMock, patch

from qlty.classes.integrations.mailtm_integration import MailTMIntegration


def _response(status_code, headers=None, body=None):
    """Build a fake requests.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = body or {}
    resp.raise_for_status.side_effect = (
        None if status_code < 400 else Exception(f"HTTP {status_code}")
    )
    return resp


class PostWithRateLimitRetryTests(unittest.TestCase):
    """
    Unit tests for MailTMIntegration._post_with_rate_limit_retry — the helper
    that absorbs mail.tm's per-IP 429s on POST /accounts.

    These tests instantiate the class via __new__ to skip __init__ (which
    would make real network calls). The retry helper is a pure method that
    only depends on requests.post and time.sleep, both patched.
    """

    def setUp(self):
        self.integration = MailTMIntegration.__new__(MailTMIntegration)
        self.url = "https://api.mail.tm/accounts"
        self.payload = {"address": "test@example.com", "password": "pw"}

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_returns_immediately_on_2xx(self, mock_post, mock_sleep):
        mock_post.return_value = _response(201, body={"address": "test@example.com"})

        response = self.integration._post_with_rate_limit_retry(self.url, self.payload)

        self.assertEqual(response.status_code, 201)
        mock_post.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_passes_through_non_429_errors_without_retry(self, mock_post, mock_sleep):
        mock_post.return_value = _response(500)

        response = self.integration._post_with_rate_limit_retry(self.url, self.payload)

        self.assertEqual(response.status_code, 500)
        mock_post.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_retries_once_on_429_then_succeeds(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            _response(429, headers={"Retry-After": "5"}),
            _response(201, body={"address": "test@example.com"}),
        ]

        response = self.integration._post_with_rate_limit_retry(self.url, self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(5)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_uses_fallback_delay_when_retry_after_missing(self, mock_post, mock_sleep):
        mock_post.side_effect = [_response(429), _response(201)]

        self.integration._post_with_rate_limit_retry(self.url, self.payload)

        mock_sleep.assert_called_once_with(MailTMIntegration._RATE_LIMIT_FALLBACK_DELAY)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_uses_fallback_delay_when_retry_after_malformed(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            _response(429, headers={"Retry-After": "not-a-number"}),
            _response(201),
        ]

        self.integration._post_with_rate_limit_retry(self.url, self.payload)

        mock_sleep.assert_called_once_with(MailTMIntegration._RATE_LIMIT_FALLBACK_DELAY)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.post")
    def test_returns_final_429_after_exhausting_retries(self, mock_post, mock_sleep):
        max_retries = MailTMIntegration._RATE_LIMIT_MAX_RETRIES
        total_attempts = max_retries + 1
        mock_post.side_effect = [_response(429, headers={"Retry-After": "1"})] * total_attempts

        response = self.integration._post_with_rate_limit_retry(self.url, self.payload)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(mock_post.call_count, total_attempts)
        # Sleeps happen between attempts, so one fewer than total
        self.assertEqual(mock_sleep.call_count, max_retries)


if __name__ == "__main__":
    unittest.main()
