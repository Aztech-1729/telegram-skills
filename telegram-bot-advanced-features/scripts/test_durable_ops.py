import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from durable_ops import Outbox, RetryDecision, retry_decision, valid_webhook_secret


class PolicyTests(unittest.TestCase):
    def test_secret_present_and_constant_comparison(self):
        self.assertTrue(valid_webhook_secret("A_secret-123", "A_secret-123"))
        self.assertFalse(valid_webhook_secret("A_secret-123", None))
        self.assertFalse(valid_webhook_secret("A_secret-123", "bad"))
        with self.assertRaises(ValueError):
            valid_webhook_secret("invalid space", "invalid space")

    def test_retry_budget_and_uncertain_mutation(self):
        self.assertEqual(retry_decision("timeout", 1).action, "uncertain")
        self.assertEqual(retry_decision("network", 1, safe_replay=True), RetryDecision("retry", 1))
        self.assertEqual(retry_decision("rate_limit", 1, retry_after=timedelta(seconds=90)).delay, 90.1)
        self.assertEqual(retry_decision("rate_limit", 4, retry_after=5).action, "failed")
        self.assertEqual(retry_decision("forbidden", 1).action, "blocked")
        self.assertEqual(retry_decision("bad_request", 1).action, "failed")
        with self.assertRaises(ValueError):
            retry_decision("rate_limit", 1, retry_after=float("nan"))


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "outbox.db"
        self.box = Outbox(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_concurrent_claim_and_dedupe_conflict(self):
        job_id = self.box.enqueue("task-1", {"text": "hello"}, now=100)
        self.assertEqual(self.box.enqueue("task-1", {"text": "hello"}, now=101), job_id)
        with self.assertRaises(ValueError):
            self.box.enqueue("task-1", {"text": "changed"}, now=101)
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(lambda _: Outbox(self.path).claim(now=100), range(8)))
        self.assertEqual(sum(job is not None for job in claims), 1)
        job = next(job for job in claims if job is not None)
        self.assertTrue(self.box.complete(job_id, job["lease_token"], now=101))
        self.assertEqual(self.box.state(job_id), "sent")

    def test_restart_expired_lease_and_stale_worker_fencing(self):
        job_id = self.box.enqueue("idempotent", {"sync": 1}, now=100, safe_replay=True)
        first = self.box.claim(now=100, lease_seconds=10)
        second = Outbox(self.path).claim(now=110, lease_seconds=10)
        self.assertEqual(second["attempts"], 2)
        self.assertFalse(self.box.complete(job_id, first["lease_token"], now=111))
        self.assertTrue(self.box.complete(job_id, second["lease_token"], now=111))

    def test_crashed_send_stops_as_uncertain(self):
        job_id = self.box.enqueue("send", {"text": "one message"}, now=100)
        self.box.claim(now=100, lease_seconds=10)
        self.assertIsNone(Outbox(self.path).claim(now=110))
        self.assertEqual(self.box.state(job_id), "uncertain")

    def test_delay_and_max_attempts_are_persisted(self):
        job_id = self.box.enqueue("retry", {"sync": 1}, now=100, safe_replay=True, max_attempts=2)
        first = self.box.claim(now=100)
        self.assertTrue(self.box.resolve_attempt(job_id, first["lease_token"], RetryDecision("retry", 50), now=101))
        self.assertIsNone(self.box.claim(now=150))
        second = Outbox(self.path).claim(now=151)
        self.assertTrue(self.box.resolve_attempt(job_id, second["lease_token"], RetryDecision("retry", 1), now=152))
        self.assertEqual(self.box.state(job_id), "failed")
        self.assertIsNone(self.box.claim(now=200))


if __name__ == "__main__":
    unittest.main()
