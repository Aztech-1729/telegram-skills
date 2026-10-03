import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets"))
from recipe_store import Store, deliver_due, public_url

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
        for value in ["javascript:alert(1)", "file:///etc/passwd", "https://user:pass@example.org", "https://example.org/ bad"]:
            with self.assertRaises(ValueError):
                public_url(value)
        code = self.store.shorten("https://example.org/a?b=1")
        self.assertEqual(len(code), 8)
        self.assertEqual(Store(self.path).resolve(code), "https://example.org/a?b=1")
        self.assertIsNone(self.store.resolve("missing"))

    def test_warnings_scoped_and_persistent(self):
        self.assertEqual(self.store.warn(1, 9), 1)
        self.assertEqual(Store(self.path).warn(1, 9), 2)
        self.assertEqual(self.store.warn(2, 9), 1)


if __name__ == "__main__":
    unittest.main()
