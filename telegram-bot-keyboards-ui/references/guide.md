# Chat UI implementation guide

Checked 2026-10-04. Contents: interaction choice; buttons and contexts; callbacks and paging; formatting and emoji; inline mode; media and UX. The [source ledger](sources.md) distinguishes Bot API support from SDK support. Examples below are integration fragments unless a runnable helper is linked.

## Choose the interaction

| Need | Mechanism | Application decision |
|---|---|---|
| Act on a result, confirm, page a list | Inline keyboard | Store ownership/version server-side; edit when useful |
| Pick a small answer set | Reply keyboard | Send removal when the flow ends; one-time hides rather than permanently deletes |
| Request contact, location, poll, users/chat | Typed `KeyboardButton` request | Check availability/context and validate returned data |
| Ask a free-text follow-up | `ForceReply` | Correlate the reply with a stored prompt and sender |
| Rich forms/catalog/game | Mini App | Choose a launch context that supports the required identity/return path |
| Share search results into another chat | Inline mode | Enable `/setinline`; define cache/pagination policy |

## Button types and context

Consult [InlineKeyboardButton](https://core.telegram.org/bots/api#inlinekeyboardbutton) and [KeyboardButton](https://core.telegram.org/bots/api#keyboardbutton) for the full schema. Important names include `callback_data`, `url`, `web_app`, `login_url`, `copy_text`, `pay`, `callback_game`, the three `switch_inline_query*` fields, and current `disabled`. `style` and `icon_custom_emoji_id` describe appearance, not an action. `pay`/`callback_game` belong first in the first row; pay is for invoice messages. An inline Web App button is for the user's private bot chat, not business-account messages. Reply keyboards are unsupported in channels and business-account messages; native contact/location requests are private-chat features.

The portable visual fallback is clear text/emoji. Native `style` selects semantic colors; Mini App `MainButton.setParams` permits RGB. Neither implies that all clients display identically. Copy-text was added in Bot API 7.11; style/icons in 9.4; timestamp entities in 9.5; disabled buttons/keyboard force-reply fields in 10.3. Check SDK constructors rather than assuming an SDK implements every server field. PTB v22.8 supports style/icons but its inspected constructor does not yet expose `disabled`; use documented `api_kwargs` only after validating the raw schema, or omit that enhancement.

PTB fragment (v22.8 style support; the surrounding application supplies `update` and `context`):

```python
from telegram import (
    ForceReply, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo,
)

menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("Confirm", callback_data="v1:confirm:42", style="success"),
     InlineKeyboardButton("Cancel", callback_data="v1:cancel:42")],
    [InlineKeyboardButton("Open app", web_app=WebAppInfo("https://app.example.com"))],
])
await update.effective_message.reply_text("Review item 42", reply_markup=menu)
contact = ReplyKeyboardMarkup(
    [[KeyboardButton("Share my contact", request_contact=True)]],
    resize_keyboard=True, one_time_keyboard=True,
)
await update.effective_message.reply_text("Contact details", reply_markup=contact)
# In the corresponding completed/canceled handler:
await update.effective_message.reply_text("Done", reply_markup=ReplyKeyboardRemove())
# For free text, use a separately correlated prompt:
await update.effective_message.reply_text("Reply with a title", reply_markup=ForceReply())
```

aiogram 3 fragment:

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

menu = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="Confirm", callback_data="v1:confirm:42", style="success"),
    InlineKeyboardButton(text="Cancel", callback_data="v1:cancel:42"),
]])
await message.answer("Review item 42", reply_markup=menu)
```

Raw `reply_markup` has `{"inline_keyboard": [[{"text": "Confirm", "callback_data": "v1:confirm:42", "style": "success"}]]}`. In Go, use the selected library's typed markup model; JSON field names do not become guessed Go struct field names. Confirm wrapper support against its versioned documentation.

Use blue `primary` for an important next action, green `success` where positive
commitment is useful, red `danger` for destructive consequences and default style
for Back/Cancel or equal peer choices. These are recommendations, not button-count
limits. A meaningful label remains necessary when clients ignore color. Read
[the UX decision table](../../telegram-bot-ux/references/guide.md#what-color-belongs-to-which-button)
for checkout, permission requests and confirmation patterns.

## Callbacks, authorization and pagination

Use [the offline helpers](../scripts/ui_helpers.py) to encode/check callbacks and build bounded page rows. Persist menu ownership and any expiry/version independently of callback text. A visible button can outlive its record. Reject unknown prefixes, invalid indices, expired records and unauthorized users with a short callback answer; return without executing the action. An opaque record ID helps compactness but does not secure access.

Answer the callback before slow I/O. Then choose the correct edit target: a chat/message pair when accessible, or `inline_message_id` for an inline result. Do not assume `callback_query.message` is present or editable. Make action execution idempotent; repeated taps can race. Suppress identical edits where practical and handle the specific 'message not modified' condition without hiding unrelated errors.

For pagination, validate against the current data snapshot, filter rows for the sender, and keep stable record IDs in buttons. A new data set may invalidate a page. The helper returns a clamped page and no empty navigation row. A cursor based on stable ordering is preferable to numeric offsets when the list changes frequently. Use an edit when it improves context, and a new message when the old result should remain available.

## Formatting, emoji and date-time

Default to the user's chosen parse mode. Escape dynamic HTML with `html.escape`; escape MarkdownV2 using the installed framework helper. HTML is not arbitrary browser HTML. For explicit entities, `offset` and `length` are **UTF-16 code units**; use the helper for text containing astral emoji. Do not mix a parse mode and a separately generated entity list without a clear reason.

An HTML date-time example with visible fallback text:

```html
Delivery by <tg-time unix="1791046800" format="wDT">2026-10-03 17:00 UTC</tg-time>
```

Raw entity shape is `{"type":"date_time","offset":0,"length":8,"unix_time":1791046800,"date_time_format":"r"}` for an eight-unit fallback string. Use the SDK's verified `MessageEntity` constructor, not guessed aliases. Custom emoji work with HTML `<tg-emoji emoji-id="...">👍</tg-emoji>` and MarkdownV2 `![👍](tg://emoji?id=...)`; preserve a valid fallback emoji. The bot needs the documented Fragment username entitlement or the owner-Premium private/group/supergroup allowance. Discover IDs by inspecting received entities/sticker metadata; third-party bots are unnecessary.

Reactions have their own constraints: at most one reaction for bots; a custom reaction must already exist on the message or be allowed by chat administrators; paid reactions are unavailable. Receiving reaction updates requires the relevant admin rights and explicit `allowed_updates`. Follow [setMessageReaction](https://core.telegram.org/bots/api#setmessagereaction) rather than equating custom-emoji message permission with reaction permission.

## Inline mode

Enable BotFather `/setinline` and register an inline-query handler. Choose result types from [inline mode](https://core.telegram.org/bots/api#inline-mode); return at most 50 results, stable IDs, a bounded cache duration and `next_offset` when additional pages exist. `is_personal` controls caching suitability; it does not authorize access to private data. Avoid placing confidential results in globally cached responses. Verify ownership again on callbacks. Provide a useful empty-result state and preserve a short query-to-result path; do not promise a universal ten-second inline deadline.

## Media, polls and interaction quality

Use media-specific send/edit methods and caption limits; a text message cannot be edited as a caption. Reuse valid `file_id` where appropriate. A media group shares some reaction behavior; test selection/edit semantics. `sendChatAction` is an expiring indicator, not completion delivery; refresh only while work remains and stop on cancellation.

For polls, match anonymity, multiple-choice and quiz behavior to the task. Current APIs include richer poll options/media; consult [sendPoll](https://core.telegram.org/bots/api#sendpoll) before choosing option/answer fields. Receive `poll_answer` only where applicable. Dice values come from Telegram, so do not promise deterministic dice results.

For long generated responses, consider current draft/rich-message APIs through the Rich Messaging skill. If editing chunks, throttle according to actual retry responses and coalesce obsolete updates; avoid universal guarantees about one edit per second. Keep destructive confirmations, accessible text labels, localized commands, cancellation and a clear terminal state. Store numeric user/chat IDs, not mutable usernames.
