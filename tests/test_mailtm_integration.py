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


class RequestWithRateLimitRetryTests(unittest.TestCase):
    """
    Unit tests for MailTMIntegration._request_with_rate_limit_retry — the helper
    that absorbs mail.tm's per-IP 429s.

    These tests instantiate the class via __new__ to skip __init__ (which
    would make real network calls). The retry helper is a pure method that
    only depends on requests.request and time.sleep, both patched.
    """

    def setUp(self):
        self.integration = MailTMIntegration.__new__(MailTMIntegration)
        self.url = "https://api.mail.tm/accounts"
        self.payload = {"address": "test@example.com", "password": "pw"}

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_returns_immediately_on_2xx(self, mock_request, mock_sleep):
        mock_request.return_value = _response(201, body={"address": "test@example.com"})

        response = self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        self.assertEqual(response.status_code, 201)
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_passes_through_non_429_errors_without_retry(self, mock_request, mock_sleep):
        mock_request.return_value = _response(500)

        response = self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        self.assertEqual(response.status_code, 500)
        mock_request.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_retries_once_on_429_then_succeeds(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "5"}),
            _response(201, body={"address": "test@example.com"}),
        ]

        response = self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once_with(5)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_uses_fallback_delay_when_retry_after_missing(self, mock_request, mock_sleep):
        mock_request.side_effect = [_response(429), _response(201)]

        self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        mock_sleep.assert_called_once_with(MailTMIntegration._RATE_LIMIT_FALLBACK_DELAY)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_uses_fallback_delay_when_retry_after_malformed(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "not-a-number"}),
            _response(201),
        ]

        self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        mock_sleep.assert_called_once_with(MailTMIntegration._RATE_LIMIT_FALLBACK_DELAY)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_clamps_excessive_retry_after_to_max_delay(self, mock_request, mock_sleep):
        # A misbehaving / malicious server returning an absurd Retry-After
        # must not hang the test indefinitely.
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "999999"}),
            _response(201),
        ]

        self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        mock_sleep.assert_called_once_with(MailTMIntegration._RATE_LIMIT_MAX_DELAY)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_clamps_negative_retry_after_to_zero(self, mock_request, mock_sleep):
        # time.sleep raises ValueError on negative input; floor at 0.
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "-5"}),
            _response(201),
        ]

        self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        mock_sleep.assert_called_once_with(0)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_returns_final_429_after_exhausting_retries(self, mock_request, mock_sleep):
        max_retries = MailTMIntegration._RATE_LIMIT_MAX_RETRIES
        total_attempts = max_retries + 1
        mock_request.side_effect = [_response(429, headers={"Retry-After": "1"})] * total_attempts

        response = self.integration._request_with_rate_limit_retry("POST", self.url, json=self.payload)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(mock_request.call_count, total_attempts)
        # Sleeps happen between attempts, so one fewer than total
        self.assertEqual(mock_sleep.call_count, max_retries)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_passes_method_and_kwargs_through_on_every_attempt(self, mock_request, mock_sleep):
        headers = {"Authorization": "Bearer t"}
        mock_request.side_effect = [_response(429, headers={"Retry-After": "1"}), _response(200)]

        self.integration._request_with_rate_limit_retry("GET", self.url, headers=headers)

        self.assertEqual(mock_request.call_count, 2)
        for call in mock_request.call_args_list:
            self.assertEqual(call.args, ("GET", self.url))
            self.assertEqual(call.kwargs, {"headers": headers})


class ReadEndpointRateLimitTests(unittest.TestCase):
    """
    GET /messages/{id} and GET /domains were the endpoints that 429'd in
    production runs once POST /accounts retried, so each must go through the
    retry helper rather than raising on the first 429.
    """

    def setUp(self):
        self.integration = MailTMIntegration.__new__(MailTMIntegration)
        self.integration._token = "t"

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_get_message_body_retries_429_then_returns_body(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "2"}),
            _response(200, body={"html": ["<a href='x'>", "y</a>"], "text": "y"}),
        ]

        body = self.integration._get_message_body("abc")

        self.assertEqual(body, {"html": "<a href='x'>y</a>", "text": "y"})
        mock_request.assert_called_with(
            "GET", "https://api.mail.tm/messages/abc", headers={"Authorization": "Bearer t"}
        )
        mock_sleep.assert_called_once_with(2)

    @patch("qlty.classes.integrations.mailtm_integration.time.sleep")
    @patch("qlty.classes.integrations.mailtm_integration.requests.request")
    def test_get_domain_retries_429_then_returns_domain(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            _response(429, headers={"Retry-After": "3"}),
            _response(200, body={"hydra:member": [{"domain": "example.com"}]}),
        ]

        self.assertEqual(self.integration._get_domain(), "example.com")
        mock_sleep.assert_called_once_with(3)


if __name__ == "__main__":
    unittest.main()
