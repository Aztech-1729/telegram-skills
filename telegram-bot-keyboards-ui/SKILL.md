---
name: telegram-bot-keyboards-ui
description: Build Telegram chat interfaces with inline and reply keyboards, callback menus, pagination, inline mode, formatted text, custom emoji, polls, media and reactions. Use for bot interaction design; use the Mini Apps skill for browser interfaces.
---

# Telegram bot keyboards and chat UI

Choose the interaction from the user's task: inline keyboards for actions on a message, reply keyboards for constrained input or native data requests, and ForceReply for a reply prompt. Do not impose one navigation style on every bot.

Read [the implementation guide](references/guide.md) for button types, PTB/aiogram patterns, pagination, inline mode, formatting and media. Read [the source/version ledger](references/sources.md) before using newer fields or explaining compatibility.

## Workflow

1. Identify framework/version, chat context, target clients and whether the interaction is a callback, native request, URL or browser UI.
2. Build a compact callback schema and server-side state. Authorize each action from the actual sender, including callbacks on forwarded/shared menus.
3. Answer callbacks promptly, then edit the relevant message when that serves the UX. Handle missing/inaccessible messages and inline-message IDs. Bound pagination and handle stale menus.
4. Escape dynamic text or construct explicit entities with UTF-16 offsets. Keep fallback labels meaningful when styling/custom emoji is unavailable.
5. Check API and installed SDK support separately. Exercise success, cancel, unauthorized, stale and malformed-input paths offline; client appearance needs a deliberate Telegram smoke test.

## Invariants

- `callback_data` is 1–64 **UTF-8 bytes**, not characters. Treat it as untrusted input; an object ID is not authorization.
- Use exact fields: `switch_inline_query`, `switch_inline_query_current_chat`, `switch_inline_query_chosen_chat`. A button has one action type; style and icon do not count as actions.
- Current inline and reply buttons support `style="primary"`, `"success"` or `"danger"`. They do not support arbitrary RGB or an inline `icon_color`/`color_id` field. Older clients may ignore style.
- Web App buttons and contact/location request buttons have chat-context restrictions; see the guide. A text label alone does not request contact/location.
- Custom emoji permissions are separate from reaction permissions. Never infer access from owning a sticker set.
- Time entities use `type="date_time"`, `unix_time`, and optional `date_time_format`. Do not invent `datetime` or `date` fields.

## Reusable resources

- [scripts/ui_helpers.py](scripts/ui_helpers.py): framework-independent byte validation, strict callback parsing, pagination and UTF-16 entity ranges.
- [scripts/test_ui_helpers.py](scripts/test_ui_helpers.py): `python -m unittest discover -s telegram-bot-keyboards-ui/scripts -p 'test_*.py'` from the repository root; no Telegram calls.

Combine with the chosen framework skill for app startup, Mini Apps for web UI, Payments for invoice buttons, or Advanced Features for durable state and sending policy.
