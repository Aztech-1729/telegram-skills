"""Deterministic failure-path tests; no internet or bot account is accessed."""
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
import sys
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_online import Target, check, fetch, retry_delay
from telegram_smoke import validate_response


class Response:
    status = 200
    def __init__(self, body=b"docs"): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.body[:limit]
    def geturl(self): return "https://example.test/docs"


class OnlineTests(unittest.TestCase):
    def test_rate_limit_retries_then_success(self):
        headers = Message()
        headers["Retry-After"] = "2"
        calls, delays = [], []
        def opener(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise HTTPError("https://example.test", 429, "slow down", headers, None)
            return Response()
        self.assertEqual(fetch("https://example.test", opener=opener, sleeper=delays.append)[0], b"docs")
        self.assertEqual(delays, [2])

    def test_not_found_is_not_retried(self):
        calls = []
        def opener(*args, **kwargs):
            calls.append(1)
            raise HTTPError("https://example.test", 404, "missing", {}, None)
        with self.assertRaisesRegex(ValueError, "HTTP 404"):
            fetch("https://example.test", opener=opener)
        self.assertEqual(len(calls), 1)

    def test_retry_after_date_and_upper_bound(self):
        now = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.assertEqual(retry_delay("Sat, 03 Oct 2026 00:00:12 GMT", 0, now=now), 12)
        self.assertEqual(retry_delay("99999", 0), 30)
        self.assertEqual(retry_delay("invalid", 2), 4)
        self.assertEqual(retry_delay("-2", 0), 0)

    def test_wrong_content_is_failure(self):
        result = check(Target("docs", "https://example.test", "Dispatcher"), fetcher=lambda _: (b"Not found", "https://example.test"))
        self.assertEqual(result["status"], "failed")

    def test_registry_json_shape(self):
        target = Target("package", "https://example.test", json_key="versions")
        for payload, expected in [(b'{"versions":["1.0"]}', "passed"), (b'{"versions":[]}', "failed"), (b"not json", "failed")]:
            with self.subTest(payload=payload):
                self.assertEqual(check(target, fetcher=lambda _: (payload, target.url))["status"], expected)

    def test_empty_response_is_failure(self):
        with self.assertRaisesRegex(ValueError, "Empty response"):
            fetch("https://example.test", opener=lambda *a, **kw: Response(b" "))

    def test_bot_identity_required(self):
        self.assertTrue(validate_response({"ok": True, "result": {"id": 1, "is_bot": True}}))
        for data in [{"ok": False}, {"ok": True, "result": {"id": True, "is_bot": True}}, {"ok": True, "result": {"id": 1, "is_bot": False}}]:
            self.assertFalse(validate_response(data))


if __name__ == "__main__":
    unittest.main()
