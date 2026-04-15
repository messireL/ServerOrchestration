from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.probes import _parse_subscription_profile_from_html


class SubscriptionHtmlParserTests(unittest.TestCase):
    def test_table_profile_ignores_generic_page_title(self) -> None:
        html = '''
        <html><head><title>Subscription Information</title></head>
        <body>
          <h1>Subscription Information</h1>
          <table>
            <tr><td>ID подписки</td><td>abc123</td></tr>
            <tr><td>Статус</td><td>Active</td></tr>
            <tr><td>Загружено</td><td>1.5 GB</td></tr>
            <tr><td>Отправлено</td><td>500 MB</td></tr>
            <tr><td>Общий лимит</td><td>10 GB</td></tr>
            <tr><td>Срок действия</td><td>2026-05-01</td></tr>
          </table>
        </body></html>
        '''
        parsed = _parse_subscription_profile_from_html(html)
        self.assertEqual(parsed.get('subscription_id'), 'abc123')
        self.assertEqual(parsed.get('profile_status'), 'Active')
        self.assertEqual(parsed.get('downloaded_bytes_text'), '1.5 GB')
        self.assertEqual(parsed.get('uploaded_bytes_text'), '500 MB')
        self.assertEqual(parsed.get('total_bytes_text'), '10 GB')
        self.assertEqual(parsed.get('expires_text'), '2026-05-01')
        self.assertNotIn('profile_title', parsed)

    def test_script_profile_parses_unquoted_keys_with_quoted_values(self) -> None:
        html = '''
        <html><body><script>
        window.profile = {
          subId: "abc123",
          download: "1.5 GB",
          upload: "500 MB",
          total: "10 GB",
          status: "Active",
          expire: "2026-05-01",
          lastOnline: "2026-04-15 10:20"
        };
        </script></body></html>
        '''
        parsed = _parse_subscription_profile_from_html(html)
        self.assertEqual(parsed.get('subscription_id'), 'abc123')
        self.assertEqual(parsed.get('downloaded_bytes_text'), '1.5 GB')
        self.assertEqual(parsed.get('uploaded_bytes_text'), '500 MB')
        self.assertEqual(parsed.get('total_bytes_text'), '10 GB')
        self.assertEqual(parsed.get('profile_status'), 'Active')
        self.assertEqual(parsed.get('expires_text'), '2026-05-01')
        self.assertEqual(parsed.get('last_seen_text'), '2026-04-15 10:20')

    def test_script_profile_rejects_html_fragments(self) -> None:
        html = '''
        <script>
        const payload = {
          title: "<div>Subscription Information</div>",
          download: "1.5 GB"
        };
        </script>
        '''
        parsed = _parse_subscription_profile_from_html(html)
        self.assertEqual(parsed.get('downloaded_bytes_text'), '1.5 GB')
        self.assertNotIn('profile_title', parsed)


if __name__ == '__main__':
    unittest.main()
