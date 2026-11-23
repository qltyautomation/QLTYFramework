import unittest
from unittest.mock import MagicMock, patch

from qlty.classes.integrations.slack_integration import SlackIntegration


class PostResultsThreadTests(unittest.TestCase):
    """
    Unit tests for SlackIntegration._post_results and its optional THREAD_TS.

    The class is instantiated via __new__ to skip __init__, which would build a
    real WebClient; the client is a mock.
    """

    def setUp(self):
        self.integration = SlackIntegration.__new__(SlackIntegration)
        self.integration.client = MagicMock()
        self.payload = {'blocks': [{'type': 'section'}]}

    def _posted_kwargs(self, slack_settings):
        with patch('qlty.classes.integrations.slack_integration.settings') as settings:
            settings.SLACK = slack_settings
            self.integration._post_results(self.payload)
        return self.integration.client.chat_postMessage.call_args.kwargs

    def test_posts_to_the_channel_without_a_thread_ts(self):
        kwargs = self._posted_kwargs({'CHANNEL_ID': 'C123'})

        self.assertEqual(kwargs['channel'], 'C123')
        self.assertEqual(kwargs['blocks'], self.payload['blocks'])
        self.assertNotIn('thread_ts', kwargs)

    def test_replies_in_the_configured_thread(self):
        kwargs = self._posted_kwargs({'CHANNEL_ID': 'C123', 'THREAD_TS': '1795193000.123456'})

        self.assertEqual(kwargs['channel'], 'C123')
        self.assertEqual(kwargs['thread_ts'], '1795193000.123456')

    def test_an_empty_thread_ts_posts_to_the_channel(self):
        # An unset env var read with os.getenv(..., None) or a blank one must not start a broken reply.
        for empty in (None, ''):
            kwargs = self._posted_kwargs({'CHANNEL_ID': 'C123', 'THREAD_TS': empty})

            self.assertNotIn('thread_ts', kwargs)


if __name__ == "__main__":
    unittest.main()
