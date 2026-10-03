import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("payloads", Path(__file__).parents[1] / "assets" / "payloads.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class PayloadTests(unittest.TestCase):
    def test_requires_exactly_one_representation(self):
        for options in ({}, {"html": "<b>x</b>", "markdown": "x"}, {"blocks": []}):
            with self.assertRaises(ValueError):
                p.rich_message(**options)

    def test_native_rich_shape(self):
        payload = p.final_rich_payload(-100123, markdown="# Report\n\nComplete")
        self.assertEqual(payload["rich_message"], {"markdown": "# Report\n\nComplete"})

    def test_draft_scope_and_stop_options(self):
        payload = p.draft_payload(123, 4, {"html": "<b>partial</b>"}, rich=True, thread_id=7, can_stop=True)
        self.assertEqual(payload["draft_id"], 4)
        self.assertEqual(payload["message_thread_id"], 7)
        self.assertTrue(payload["can_stop"])
        self.assertNotIn("text", payload)

    def test_invalid_draft_identity(self):
        for chat, draft in ((-1, 2), (0, 2), (123, 0), (True, 2), (123, True)):
            with self.assertRaises(ValueError):
                p.draft_payload(chat, draft, "partial")

    def test_plain_empty_draft_is_allowed(self):
        self.assertEqual(p.draft_payload(123, 1, "")["text"], "")

if __name__ == "__main__":
    unittest.main()
