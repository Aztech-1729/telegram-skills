import unittest
from ui_helpers import check_callback, page_rows, parse_callback, utf16_range


class UIHelpersTests(unittest.TestCase):
    def test_bytes_not_characters(self):
        self.assertEqual(check_callback("😀" * 16), "😀" * 16)
        for value in ("", "😀" * 17):
            with self.assertRaises(ValueError):
                check_callback(value)

    def test_schema_rejects_unknown_negative_and_unicode_digits(self):
        self.assertEqual(parse_callback("v1:page:12"), ("page", 12))
        for value in ("v2:page:1", "v1:page:-1", "v1:page:１", "v1:item:1:extra", "v1:page:1\n"):
            with self.assertRaises(ValueError):
                parse_callback(value)

    def test_utf16_emoji_range(self):
        self.assertEqual(utf16_range("A😀B👍", 3, 4), (4, 2))
        with self.assertRaises(ValueError):
            utf16_range("abc", 2, 2)

    def test_pagination_boundaries_and_empty_rows(self):
        items = [(i, str(i)) for i in range(12)]
        page, rows = page_rows(items, 100, 5)
        self.assertEqual(page, 2)
        self.assertEqual(rows[0][0]["callback_data"], "v1:item:10")
        self.assertEqual(rows[-1], [{"text": "Previous", "callback_data": "v1:page:1"}])
        self.assertEqual(page_rows([], -9), (0, []))
        self.assertEqual(len(page_rows(items[:2], 0)[1]), 2)


if __name__ == "__main__":
    unittest.main()
