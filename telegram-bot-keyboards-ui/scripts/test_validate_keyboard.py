import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate_keyboard import validate_inline_keyboard


def markup(*buttons):
    return {"inline_keyboard": [list(buttons)]}


class KeyboardValidationTests(unittest.TestCase):
    def test_normal_menu_and_empty_markup_are_accepted_without_mutation(self):
        value = markup({"text": "Confirm", "callback_data": "v1:confirm:42", "style": "success"},
                       {"text": "Cancel", "callback_data": "v1:cancel:42"})
        snapshot = copy.deepcopy(value)
        self.assertEqual(validate_inline_keyboard(value)["errors"], [])
        self.assertEqual(value, snapshot)
        self.assertEqual(validate_inline_keyboard({"inline_keyboard": []})["errors"], [])

    def test_multiple_or_missing_actions_fail_but_empty_queries_and_disabled_work(self):
        for button in ({"text": "Missing"}, {"text": "Both", "url": "https://example.org", "callback_data": "x"},
                       {"text": "Disabled", "disabled": {}, "callback_data": "x"}):
            with self.subTest(button=button):
                self.assertTrue(validate_inline_keyboard(markup(button))["errors"])
        for action in ("switch_inline_query", "switch_inline_query_current_chat"):
            self.assertEqual(validate_inline_keyboard(markup({"text": "Search", action: ""}))["errors"], [])
        self.assertEqual(validate_inline_keyboard(markup({"text": "Unavailable", "disabled": {}}))["errors"], [])

    def test_callback_utf8_boundaries_and_malformed_unicode(self):
        self.assertEqual(validate_inline_keyboard(markup({"text": "Pick", "callback_data": "😀" * 16}))["errors"], [])
        for data in ("😀" * 17, "", 123, None, "\ud800"):
            self.assertTrue(validate_inline_keyboard(markup({"text": "Pick", "callback_data": data}))["errors"])

    def test_pay_and_game_require_first_position_and_pay_requires_invoice(self):
        pay, game = {"text": "Buy", "pay": True}, {"text": "Play", "callback_game": {}}
        self.assertEqual(validate_inline_keyboard(markup(pay), invoice=True)["errors"], [])
        self.assertTrue(validate_inline_keyboard(markup(pay), invoice=False)["errors"])
        self.assertTrue(validate_inline_keyboard(markup(pay))["warnings"])
        self.assertEqual(validate_inline_keyboard(markup(game))["errors"], [])
        for button in (pay, game):
            wrong_column = markup({"text": "Back", "callback_data": "x"}, button)
            wrong_row = {"inline_keyboard": [[{"text": "Back", "callback_data": "x"}], [button]]}
            self.assertTrue(validate_inline_keyboard(wrong_column, invoice=True)["errors"])
            self.assertTrue(validate_inline_keyboard(wrong_row, invoice=True)["errors"])
        for value in (False, 1, "true"):
            self.assertTrue(validate_inline_keyboard(markup({"text": "Buy", "pay": value}), invoice=True)["errors"])

    def test_copy_text_character_bounds_and_unknown_fields(self):
        for value in ("a", "😀" * 256):
            self.assertEqual(validate_inline_keyboard(markup({"text": "Copy", "copy_text": {"text": value}}))["errors"], [])
        for value in ("", "a" * 257, None):
            self.assertTrue(validate_inline_keyboard(markup({"text": "Copy", "copy_text": {"text": value}}))["errors"])
        self.assertTrue(validate_inline_keyboard(markup({"text": "Copy", "copy_text": {"text": "x", "callback_data": "x"}}))["errors"])

    def test_webapp_and_login_https_and_context_restrictions(self):
        app = markup({"text": "Open", "web_app": {"url": "https://app.example.org"}})
        self.assertEqual(validate_inline_keyboard(app, chat_type="private")["errors"], [])
        for context in ({"chat_type": "group"}, {"chat_type": "private", "business": True}):
            self.assertTrue(validate_inline_keyboard(app, **context)["errors"])
        for url in ("http://app.example.org", "https://", "javascript:alert(1)", "https://app.example.org:bad", "https://app.example.org/a\nb"):
            self.assertTrue(validate_inline_keyboard(markup({"text": "Open", "web_app": {"url": url}}))["errors"])
        login = markup({"text": "Sign in", "login_url": {"url": "https://example.org", "request_write_access": False}})
        self.assertEqual(validate_inline_keyboard(login)["errors"], [])
        self.assertTrue(validate_inline_keyboard(login, ephemeral=True)["errors"])

    def test_inline_switch_context_and_flags(self):
        chosen = markup({"text": "Share", "switch_inline_query_chosen_chat": {"allow_group_chats": True}})
        self.assertEqual(validate_inline_keyboard(chosen)["errors"], [])
        for context in ({"business": True}, {"chat_type": "channel_direct"}):
            self.assertTrue(validate_inline_keyboard(chosen, **context)["errors"])
        self.assertTrue(validate_inline_keyboard(markup({"text": "Share", "switch_inline_query_current_chat": ""}), chat_type="channel")["errors"])
        for flag in (1, "true", None):
            self.assertTrue(validate_inline_keyboard(markup({"text": "Share", "switch_inline_query_chosen_chat": {"allow_group_chats": flag}}))["errors"])

    def test_style_shape_and_optional_booleans(self):
        for value in (None, [], {"inline_keyboard": "rows"}, {"inline_keyboard": ["row"]}, markup("button"),
                      markup({"text": "X", "callback_data": "x", "style": "link"}),
                      {"inline_keyboard": [], "force_reply": "true"},
                      markup({"text": "X", "callback_data": "x", "color_id": 1})):
            self.assertTrue(validate_inline_keyboard(value)["errors"])
        self.assertEqual(validate_inline_keyboard({"inline_keyboard": [], "force_reply": False})["errors"], [])
        with self.assertRaises(ValueError):
            validate_inline_keyboard(markup({"text": "Buy", "pay": True}), invoice="true")

    def test_ui_warnings_do_not_invent_api_limits(self):
        value = markup({"text": " ", "callback_data": "x", "icon_custom_emoji_id": "123"})
        report = validate_inline_keyboard(value)
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(report["warnings"]), 2)

    def test_cli_exit_status_duplicate_keys_and_no_input_values_in_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "keyboard.json"
            command = [sys.executable, str(Path(__file__).with_name("validate_keyboard.py")), str(path)]
            for content, status in ((json.dumps(markup({"text": "OK", "callback_data": "x"})), 0),
                                    ('{"inline_keyboard":[],"inline_keyboard":[]}', 1),
                                    (json.dumps(markup({"text": "Secret", "callback_data": "private-value" * 10})), 1)):
                path.write_text(content, encoding="utf-8")
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(bool(json.loads(result.stdout)["errors"]), bool(status))
                self.assertNotIn("private-value", result.stdout)


if __name__ == "__main__":
    unittest.main()
