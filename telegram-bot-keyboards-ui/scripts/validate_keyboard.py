"""Offline InlineKeyboardMarkup checks for Bot API 10.3; no transport or SDK.

This checks the listed fields, not bot rights, domain registration, ownership,
client rendering or every surrounding message constraint. Errors never echo values.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from ui_helpers import check_callback

ACTIONS = frozenset({"url", "callback_data", "web_app", "login_url", "copy_text",
                     "callback_game", "pay", "disabled", "switch_inline_query",
                     "switch_inline_query_current_chat", "switch_inline_query_chosen_chat"})
BUTTON_FIELDS = ACTIONS | {"text", "style", "icon_custom_emoji_id"}
CHAT_TYPES = {"private", "group", "supergroup", "channel", "channel_direct"}


def validate_inline_keyboard(markup, *, chat_type=None, business=False, invoice=None, ephemeral=False):
    """Return errors/warnings without modifying markup. Unknown fields fail closed.

    None means the chat/invoice context is unknown. Warnings are review prompts,
    not Telegram limits. A valid result does not authorize an action.
    """
    errors, warnings = [], []

    def error(path, message):
        errors.append({"path": path, "message": message})

    def warn(path, message):
        warnings.append({"path": path, "message": message})

    def fields(value, allowed, required, path):
        if not isinstance(value, dict):
            error(path, "Expected an object")
            return False
        if set(value) - allowed:
            error(path, "Unknown field; compare with the reviewed API schema")
        if required - set(value):
            error(path, "Required field missing")
        return True

    def string(value, path):
        if not isinstance(value, str):
            error(path, "Expected a string")
            return False
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            error(path, "Expected valid Unicode scalar values")
            return False
        return True

    def url(value, path, https=False):
        if not string(value, path):
            return
        try:
            parsed = urlsplit(value)
            parsed.port
            valid = (parsed.scheme in ({"https"} if https else {"http", "https", "tg"})
                     and bool(parsed.hostname)
                     and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value))
        except ValueError:
            valid = False
        if not valid:
            error(path, "Expected an absolute HTTPS URL" if https else "Expected an absolute HTTP(S) or tg URL")

    if chat_type is not None and chat_type not in CHAT_TYPES:
        raise ValueError("Unsupported chat context")
    if type(business) is not bool or type(ephemeral) is not bool or (invoice is not None and type(invoice) is not bool):
        raise ValueError("Context flags must be booleans")
    if not fields(markup, {"inline_keyboard", "force_reply"}, {"inline_keyboard"}, "$"):
        return {"errors": errors, "warnings": warnings}
    if "force_reply" in markup and type(markup["force_reply"]) is not bool:
        error("$.force_reply", "Expected a boolean")
    rows = markup.get("inline_keyboard")
    if not isinstance(rows, list):
        error("$.inline_keyboard", "Expected an array of rows")
        return {"errors": errors, "warnings": warnings}
    for r, row in enumerate(rows):
        row_path = f"$.inline_keyboard[{r}]"
        if not isinstance(row, list):
            error(row_path, "Expected an array of buttons")
            continue
        for c, button in enumerate(row):
            path = f"{row_path}[{c}]"
            if not fields(button, BUTTON_FIELDS, {"text"}, path):
                continue
            if string(button.get("text"), path + ".text") and not button["text"].strip():
                warn(path + ".text", "Choose a meaningful visible label")
            if "style" in button and button["style"] not in ("primary", "success", "danger"):
                error(path + ".style", "Use primary, success or danger; RGB and link are not inline styles")
            if "icon_custom_emoji_id" in button:
                string(button["icon_custom_emoji_id"], path + ".icon_custom_emoji_id")
                warn(path, "Custom emoji permission and client support need a separate check")
            actions = ACTIONS.intersection(button)
            if len(actions) != 1:
                error(path, "Specify exactly one action field, including disabled")
            for action in sorted(actions):
                value, target = button[action], path + "." + action
                if action == "callback_data":
                    try:
                        check_callback(value)
                    except (ValueError, UnicodeEncodeError):
                        error(target, "Use 1–64 UTF-8 bytes")
                elif action == "url":
                    url(value, target)
                elif action in {"switch_inline_query", "switch_inline_query_current_chat"}:
                    string(value, target)  # An empty query is valid.
                elif action in {"callback_game", "disabled"}:
                    if not isinstance(value, dict) or value:
                        error(target, "The reviewed schema requires an empty object")
                elif action == "pay":
                    if value is not True:
                        error(target, "A Pay action must be true")
                    if invoice is False:
                        error(target, "Pay is supported only on an invoice message")
                    elif invoice is None:
                        warn(target, "Confirm that the containing message is an invoice")
                elif action == "copy_text":
                    if fields(value, {"text"}, {"text"}, target) and string(value.get("text"), target + ".text"):
                        if not 1 <= len(value["text"]) <= 256:
                            error(target + ".text", "Use 1–256 characters")
                elif action in {"web_app", "login_url"}:
                    allowed = {"url"} if action == "web_app" else {"url", "forward_text", "bot_username", "request_write_access"}
                    if fields(value, allowed, {"url"}, target):
                        url(value.get("url"), target + ".url", https=True)
                        for key in ("forward_text", "bot_username"):
                            if key in value:
                                string(value[key], target + "." + key)
                        if "request_write_access" in value and type(value["request_write_access"]) is not bool:
                            error(target + ".request_write_access", "Expected a boolean")
                elif action == "switch_inline_query_chosen_chat":
                    flags = {"allow_user_chats", "allow_bot_chats", "allow_group_chats", "allow_channel_chats"}
                    if fields(value, flags | {"query"}, set(), target):
                        if "query" in value:
                            string(value["query"], target + ".query")
                        for key in flags.intersection(value):
                            if type(value[key]) is not bool:
                                error(target + "." + key, "Expected a boolean")
                if action in {"pay", "callback_game"} and (r, c) != (0, 0):
                    error(target, "Must be the first button in the first row")
                if action == "web_app" and (business or (chat_type is not None and chat_type != "private")):
                    error(target, "Requires a private user/bot chat and no business sender")
                if action == "login_url" and ephemeral:
                    error(target, "Login URLs are unsupported in ephemeral messages")
                if action.startswith("switch_inline_query"):
                    if business or chat_type == "channel_direct" or (action == "switch_inline_query_current_chat" and chat_type == "channel"):
                        error(target, "Inline switching is unsupported in this context")
    return {"errors": errors, "warnings": warnings}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSON InlineKeyboardMarkup file")
    parser.add_argument("--chat-type", choices=sorted(CHAT_TYPES))
    parser.add_argument("--business", action="store_true")
    parser.add_argument("--invoice", action="store_true", help="The containing message is an invoice")
    parser.add_argument("--ephemeral", action="store_true")
    args = parser.parse_args()
    try:
        markup = json.loads(args.path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        report = validate_inline_keyboard(markup, chat_type=args.chat_type, business=args.business,
                                          invoice=args.invoice, ephemeral=args.ephemeral)
    except (OSError, UnicodeError, ValueError, RecursionError):
        report = {"errors": [{"path": "$", "message": "Cannot read a valid JSON object with unique fields"}], "warnings": []}
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
