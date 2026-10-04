import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import sqlite3
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets"))
from recipe_store import Store, deliver_due, public_url, text_parts

QUESTIONS = [("Q", ["A", "B"], 0)]


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "recipes.db"
        self.store = Store(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_quiz_rejects_ownership_expiry_and_bad_choice(self):
        key = self.store.new_quiz(1, 2, now=100)
        for values in [(9, 2, 0, 0, 101), (1, 9, 0, 0, 101), (1, 2, 0, 9, 101), (1, 2, 0, 0, 4000)]:
            user, chat, step, choice, now = values
            with self.assertRaises(ValueError):
                self.store.answer(key, user, chat, step, choice, QUESTIONS, now)
        self.assertTrue(self.store.answer(key, 1, 2, 0, 0, QUESTIONS, 101))
        with self.assertRaises(ValueError):
            self.store.answer(key, 1, 2, 0, 0, QUESTIONS, 101)

    def test_concurrent_answers_score_once(self):
        key = self.store.new_quiz(1, 2)
        def attempt(_):
            try:
                return self.store.answer(key, 1, 2, 0, 0, QUESTIONS)
            except ValueError:
                return False
        with ThreadPoolExecutor(4) as pool:
            self.assertEqual(sum(pool.map(attempt, range(8))), 1)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT score FROM scores WHERE user=1").fetchone(), (1,))

    def test_failed_delivery_stays_pending_and_success_persists(self):
        self.store.remind(1, "test", 100)
        async def fail(*args):
            raise RuntimeError("network unavailable")
        with self.assertRaises(RuntimeError):
            asyncio.run(deliver_due(self.store, fail, 101))
        self.assertEqual(len(Store(self.path).due(101)), 1)
        delivered = []
        async def send(*args):
            delivered.append(args)
        asyncio.run(deliver_due(self.store, send, 101))
        self.assertEqual(delivered, [(1, "Reminder: test")])
        self.assertEqual(Store(self.path).due(101), [])

    def test_shortener_roundtrip_and_schemes(self):
        for value in ["javascript:alert(1)", "file:///etc/passwd", "https://user:pass@example.org", "https://example.org/ bad", "https://example.org/a\nb", "https://example.org:wrong"]:
            with self.assertRaises(ValueError):
                public_url(value)
        code = self.store.shorten("https://example.org/a?b=1")
        self.assertEqual(len(code), 8)
        self.assertEqual(Store(self.path).resolve(code), "https://example.org/a?b=1")
        self.assertIsNone(self.store.resolve("missing"))

    def test_chunks_preserve_text_with_astral_characters(self):
        text = "A" + "😀" * 4000 + " end"
        parts = list(text_parts(text))
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(0 < len(part.encode("utf-16-le")) // 2 <= 4000 for part in parts))

    def test_reminder_ownership_retry_isolation_and_topic(self):
        blocked = self.store.remind(1, "blocked", 100, user=7)
        good = self.store.remind(2, "topic", 100, user=8, thread=44)
        retry = self.store.remind(3, "retry", 100, user=9)
        delivered = []
        async def send(chat, text, **kwargs):
            if chat != 2:
                raise RuntimeError("do not retain this sensitive exception body")
            delivered.append((chat, text, kwargs))
        attempts = iter([None, 50])
        asyncio.run(deliver_due(self.store, send, 101, lambda error, attempt: next(attempts), clock=lambda: 101))
        self.assertEqual(delivered, [(2, "Reminder: topic", {"message_thread_id": 44})])
        self.assertEqual(self.store.due(150), [])
        self.assertEqual(Store(self.path).due(151)[0][0], retry)
        self.assertFalse(self.store.cancel_reminder(retry, 8, 3))
        self.assertFalse(self.store.cancel_reminder(retry, 9, 2))
        self.assertTrue(self.store.cancel_reminder(retry, 9, 3))
        self.assertFalse(self.store.cancel_reminder(retry, 9, 3))
        self.assertEqual(self.store.reminders(7, 1)[0][3], 1)
        bounded = self.store.remind(4, "bounded", 100, user=10)
        async def always_fail(*args, **kwargs):
            raise RuntimeError("redact me")
        for _ in range(5):
            asyncio.run(deliver_due(self.store, always_fail, 151, lambda error, attempt: 0, clock=lambda: 151))
        self.assertEqual(self.store.due(151), [])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT attempts,last_error,failed FROM reminders WHERE id=?", (bounded,)).fetchone(),
                             (5, "RuntimeError", 1))

    def test_earlier_reminder_schema_migrates_and_keeps_pending_work(self):
        old_path = Path(self.temp.name) / "old.db"
        db = sqlite3.connect(old_path)
        try:
            db.execute("CREATE TABLE reminders(id INTEGER PRIMARY KEY,chat INTEGER,text TEXT,due INTEGER,done INTEGER NOT NULL DEFAULT 0)")
            db.execute("INSERT INTO reminders VALUES(1,2,'existing',100,0)")
            db.commit()
        finally:
            db.close()
        old = Store(old_path)
        self.assertEqual(old.due(101)[0][:3], (1, 2, "existing"))
        self.assertFalse(old.cancel_reminder(1, 7, 2))

    def test_rate_limit_pauses_remaining_batch_across_restart(self):
        first = self.store.remind(1, 'first', 100)
        second = self.store.remind(2, 'second', 100)
        attempts = []
        async def rate_limited(chat, text):
            attempts.append(chat)
            raise RuntimeError('rate limit')
        asyncio.run(deliver_due(self.store, rate_limited, 101, lambda error, attempt: 90,
                               pause_on_error=lambda error: True, clock=lambda: 101))
        self.assertEqual(attempts, [1])
        self.assertEqual(Store(self.path).due(190), [])
        self.assertEqual([row[0] for row in Store(self.path).due(191)], [first, second])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT attempts FROM reminders WHERE id=?', (second,)).fetchone(), (0,))

    def test_warnings_scoped_and_persistent(self):
        self.assertEqual(self.store.warn(1, 9), 1)
        self.assertEqual(Store(self.path).warn(1, 9), 2)
        self.assertEqual(self.store.warn(2, 9), 1)

    def test_slow_batch_rate_limit_starts_when_error_arrives(self):
        self.store.remind(1, 'slow success', 100)
        failed = self.store.remind(2, 'limited', 100)
        pending = self.store.remind(3, 'not attempted', 100)
        current = [101]
        attempts = []

        async def send(chat, text):
            attempts.append(chat)
            current[0] += 60
            if chat == 2:
                raise RuntimeError('rate limit received at 221')

        asyncio.run(deliver_due(self.store, send, 101, lambda error, attempt: 90,
                               pause_on_error=lambda error: True, clock=lambda: current[0]))
        self.assertEqual(attempts, [1, 2])
        self.assertEqual(Store(self.path).due(310), [])
        self.assertEqual([row[0] for row in Store(self.path).due(311)], [failed, pending])

    def test_transient_retry_starts_at_failure_with_fractional_clock(self):
        reminder = self.store.remind(1, 'retry', 100)

        async def fail(*args):
            raise RuntimeError('late network failure')

        asyncio.run(deliver_due(self.store, fail, 101, lambda error, attempt: 30,
                               clock=lambda: 200.25))
        self.assertEqual(Store(self.path).due(230), [])
        self.assertEqual(Store(self.path).due(231)[0][0], reminder)


if __name__ == "__main__":
    unittest.main()
