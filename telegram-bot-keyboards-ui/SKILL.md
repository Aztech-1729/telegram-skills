---
name: |
  telegram-bot-keyboards-ui
description: |
  Load this skill for Telegram bot UI work: inline keyboards, reply keyboards, button types (callback, URL, web_app, switch_inline, login, pay, copy_text), pagination patterns, menus, text formatting (HTML and MarkdownV2), message editing, media messages, polls, force reply, and UX patterns for bots with complete examples for python-telegram-bot, aiogram, and raw Bot API.
---

# Telegram Bot UI: Keyboards, Buttons, Formatting & UX

## 1. The two keyboard types

- **Inline keyboards** — attached to a message; buttons send `callback_data` to the bot. Best for menus, pagination, confirmation. Editable after sending.
- **Reply keyboards** — replace the user's typing keyboard; tapping sends a normal text message. Best for constrained input flows (Yes/No, share contact/location). Persistent per chat until replaced/removed.

Never use reply keyboards for navigation; use inline.

## 2. Inline button types (complete)

| Button | What it does |
|---|---|
| `callback_data` | Sends ≤64-byte string to bot as `callback_query` |
| `url` | Opens a URL |
| `web_app` | Opens a Mini App (HTTPS only) |
| `switch_inline` / `switch_inline_current_chat` | Inserts `@bot query` into the input |
| `login_url` | Telegram Login Widget flow |
| `pay` | Payments (Bot API invoices) |
| `copy_text` | Copies text to clipboard (Bot API 9.0+) |

**Button appearance fields (latest Bot API)**: `InlineKeyboardButton` also accepts:
- `icon_color` — color ID from a fixed palette (0 red, 1 orange, 2 purple/violet, 3 green, 4 cyan, 5 blue, 6 pink — customizable by app themes). Rendered for **Mini App keyboard buttons** (dialogs shown inside a Mini App).
- `icon_custom_emoji_id` — shows a custom emoji on the button, if the bot can use custom emoji in the message.

Plain inline keyboard buttons in normal chats render with the client's default style — `icon_color` only takes effect in Mini App dialog keyboards.

## 3. python-telegram-bot

```python
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Confirm", callback_data="confirm:yes"),
     InlineKeyboardButton("❌ Cancel", callback_data="confirm:no")],
    [InlineKeyboardButton("🌐 Open site", url="https://example.com"),
     InlineKeyboardButton("🚀 Mini app", web_app=WebAppInfo(url="https://app.example.com"))],
])
await update.message.reply_text("Confirm?", reply_markup=kb)

# Editing after a tap — swap keyboard out
async def on_confirm(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Confirmed ✅")   # reply_markup auto-cleared
```

```python
from telegram import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply,
)

kb = ReplyKeyboardMarkup(
    [["📍 Share location", "📱 Share contact"]],
    one_time_keyboard=True, resize_keyboard=True, is_persistent=False,
    input_field_placeholder="Choose...",
    # KeyboardButton(text="📍 Share location", request_location=True),
    # KeyboardButton(text="📱 Share contact", request_contact=True),
    # KeyboardButton(text="🗳 Send poll", request_poll=KeyboardButtonPollType(type="regular")),
)
await update.message.reply_text("Please pick:", reply_markup=kb)
await update.message.reply_text("Done", reply_markup=ReplyKeyboardRemove())  # remove
```

## 4. aiogram 3

```python
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)

kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Confirm", callback_data="confirm:yes")],
    [InlineKeyboardButton(text="Site", url="https://example.com")],
    [InlineKeyboardButton(text="Mini app", web_app=WebAppInfo(url="https://app.example.com"))],
])
await message.answer("Confirm?", reply_markup=kb)
await cb.message.edit_text("Confirmed")   # after CallbackQueryHandler
```

```python
rkb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Yes"), KeyboardButton(text="No")]],
    resize_keyboard=True, one_time_keyboard=True,
)
await message.answer("Pick:", reply_markup=rkb)
await message.answer("Thanks!", reply_markup=ReplyKeyboardRemove())
```

## 5. Raw Bot API JSON

```json
{
  "chat_id": 123,
  "text": "Confirm?",
  "reply_markup": {
    "inline_keyboard": [[
      {"text": "Confirm", "callback_data": "confirm:yes"},
      {"text": "Site", "url": "https://example.com"}
    ]]
  }
}
```

## 6. Pagination pattern (works in all libraries)

```python
# Paged list with callback data "page:<n>"
PAGES = [["alpha", "beta"], ["gamma", "delta"]]

def page_kb(page: int):
    nav = []
    if page > 0:
        nav.append(("◀️", f"page:{page-1}"))
    if page < len(PAGES) - 1:
        nav.append(("▶️", f"page:{page+1}"))
    return [[(f"{i+1}. {item}", f"item:{page}:{i}")] for i, item in enumerate(PAGES[page])] + [nav]

async def show(update, context):
    await update.message.reply_text("Results page 0", reply_markup=build(page_kb(0)))

async def on_page(update, context):
    q = update.callback_query
    await q.answer()
    page = int(q.data.split(":")[1])
    await q.edit_message_text(f"Results page {page}", reply_markup=build(page_kb(page)))
```

Where `build()` converts (label, data) pairs into the library's markup class. Always `edit_message_text` rather than sending new messages when navigating.

## 7. Inline mode results

Enable via BotFather `/setinline`. The user types `@yourbot query` in ANY chat:

```python
# PTB
from telegram import (
    InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, InlineQueryResultCachedPhoto,
)

async def inline(update, context):
    q = update.inline_query
    items = search(q.query)
    await q.answer([
        InlineQueryResultArticle(
            id=str(i), title=item.title, description=item.desc,
            input_message_content=InputTextMessageContent(item.text),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open", url=item.url)]]),
        ) for i, item in enumerate(items[:50])
    ], cache_time=60, is_personal=True, next_offset="")
```

Result types: `Article`, `Photo`, `Gif`, `Mpeg4Gif`, `Video`, `Audio`, `Voice`, `Document`, `Location`, `Venue`, `Contact`, `Game`, `CachedPhoto/Audio/Video/...` (by file_id). Answer within ~10s; use `next_offset` for pagination of >50 results.

## 8. Text formatting — HTML (preferred)

```python
<b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>,
<tg-spoiler>spoiler</tg-spoiler>, <a href="https://example.com">link</a>,
<a href="tg://user?id=123456">name link</a>,
<code>inline code</code>, <pre>block code</pre>,
<pre><code class="language-python">print('hi')</code></pre>,
<blockquote>quote</blockquote>, <blockquote expandable>long quote</blockquote>
```

Python:

```python
import html
safe = html.escape(user_input)
await bot.send_message(chat_id, f"User said: <code>{safe}</code>", parse_mode="HTML")
```

MarkdownV2 escape set: `_ * [ ] ( ) ~ \` > # + - = | { } . !` — escape dynamic text with `telegram.helpers.escape_markdown(text, version=2)` / aiogram's `aiogram.utils.markdown` helpers. Prefer HTML for anything containing user input.

## 8.5 Premium / custom emoji and reactions (custom_emoji_id)

**Custom (premium) emoji** are sent via a special HTML entity with the emoji's numeric `custom_emoji_id`:

```html
Nice! <tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
```

The tag content is a fallback emoji shown by old clients; bots can use custom emoji only in some contexts (they must own/be admin of the sticker set or use allowed ones). Other parse modes: MarkdownV2 has no syntax for it — use HTML, or the JSON input (entities) API.

Libraries:

```python
# PTB — custom emoji entity via HTML
await bot.send_message(chat_id, 'Hi <tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>',
                       parse_mode=ParseMode.HTML)
# Raw entity form (no parse mode): pass text + entities
from telegram import MessageEntity
await bot.send_message(chat_id, "Hi 👍",
    entities=[MessageEntity(MessageEntity.CUSTOM_EMOJI, offset=3, length=2,
                            custom_emoji_id="5368324170671202286")])

# aiogram 3
await message.answer('Hi <tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>')
# typed entity:
from aiogram.types import MessageEntity
entities=[MessageEntity(type="custom_emoji", offset=3, length=2,
                         custom_emoji_id="5368324170671202286")]

# Fetch emoji stickers / preview custom emoji by IDs
await bot.get_custom_emoji_stickers(["5368324170671202286"])   # both libraries
# aiogram 3.31+: await bot.get_custom_emoji_stickers(custom_emoji_ids=[...])
```

How to find a `custom_emoji_id`: forward a message containing the premium emoji to @RmojiRawBot or inspect the message's `entities`/`caption_entities` (`entity.custom_emoji_id`), or read it from your own sticker set via `get_sticker_set`. IDs are large integers (as strings), per-emoji, permanent.

**Permission rules for custom emoji (exact, per Bot API docs):** a bot may use custom emoji entities only if (a) the bot purchased additional usernames on Fragment, OR (b) in messages directly sent by the bot to private/group/supergroup chats **while the bot owner has Telegram Premium**. The fallback emoji shows in notifications and when forwarded by non-premium users. Use the emoji from the custom emoji sticker's `emoji` field as the fallback. Bots **cannot use paid reactions**.

**Date/time entities (rendered per-user locale!)** — dynamic timestamps that each user sees in their own timezone/language:

```html
Order in 10 minutes → arrives by <tg-time unix="1760000000" format="wDT"></tg-time>
```

```python
# PTB MarkdownV2 / entity form:
MessageEntity(type="datetime", offset=..., length=..., date=datetime(2026, 10, 3, 18, 0))
# aiogram: MessageEntity(type="datetime", offset=..., length=..., date=...)
```

Formats: plain (auto), `wDT`/`t`/`r` (relative — "in 10 minutes") etc. Perfect for countdowns, delivery ETAs, subscription expiry — never hardcode a timezone string again.

```python
# PTB
await bot.set_message_reaction(chat_id, message_id, [ReactionTypeCustomEmoji("5368324170671202286")])
# aiogram
await bot.set_message_reaction(chat_id=chat_id, message_id=mid,
    reaction=[ReactionTypeCustomEmoji(custom_emoji_id="5368324170671202286")])
```

## 8.6 Button colors — the truth + what IS available

The Bot API does **not** let you color inline/reply keyboard buttons. Buttons render with client-side styling only. What exists:

1. **Mini App JS buttons** — the ONLY place with real button colors:
   - `showPopup` buttons accept `type: "default" | "destructive" | "cancel"` (destructive renders red).
   - `MainButton.setParams({ color: "#RRGGBB", text_color: "#RRGGBB" })` — full RGB on the main button.
   - Back/secondary buttons follow `themeParams.button_color`.
   - Mini App keyboard buttons (`KeyboardButton` in Mini App dialogs) accept `color_id` from a fixed palette (0 red, 1 orange, 2 purple, 3 green, 4 cyan, 5 blue, 6 pink — customizable by app themes); `text_color_id` likewise.
2. **Native-client illusion**: green "✅"/red "❌" buttons you see in other bots are just emoji labels — the standard trick:

```python
[
    InlineKeyboardButton("✅ Confirm", callback_data="confirm:yes"),   # looks green-ish
    InlineKeyboardButton("❌ Cancel",  callback_data="confirm:no"),   # looks red-ish
]
```

3. `force_reply` / reply keyboards have no color params either.

Rule for agents: never invent a `color` param for Bot API buttons — it doesn't exist; use emoji-prefix styling or a Mini App when color really matters. (Copy_text buttons and web_app buttons also render with the default client style.)

## 9. Media UX patterns

```python
# Typing/upload indicators (auto-expire after 5s or message send)
await bot.send_chat_action(chat_id, "typing")     # typing | upload_photo | record_video |
                                                 # upload_document | choose_sticker | find_location
# For long tasks, loop the indicator every 4-5 s

# Photo with caption entities
await bot.send_photo(chat_id, photo, caption="<b>Report</b> — Q3", parse_mode="HTML")

# Progressive AI-style message (edit in chunks; avoid >1 edit/second to prevent flood limits)
text = long_answer()
for i in range(1, min(len(text), 400) + 1, 100):
    await bot.edit_message_text(text[:i], chat_id, msg_id)
# Note: editing the same message too fast triggers 429 — throttle to ~1/s

# Polls
await bot.send_poll(
    chat_id, "Best language?", ["Python", "Go", "Rust"],
    is_anonymous=False, allows_multiple_answers=False,
)

# Dice / reactions
await bot.send_dice(chat_id, emoji="🎲")  # dice, darts, basketball, football, bowling, slot
await bot.set_message_reaction(chat_id, message_id, reaction=[ReactionTypeEmoji("👍")])
```

## 9.5 Go snippets (for the Go skills)

```go
// go-telegram/bot
b.SendMessage(ctx, &bot.SendMessageParams{ChatID: id, Text: "Choose:",
    ReplyMarkup: models.InlineKeyboardMarkup{InlineKeyboard: [][]models.InlineKeyboardButton{{
        {Text: "Tap", CallbackData: "act:1"},
    }}}})

// gotgbot
ctx.EffectiveMessage.Reply(b, "Choose?", &gotgbot.SendMessageOpts{
    ReplyMarkup: &gotgbot.InlineKeyboardMarkup{InlineKeyboard: [][]gotgbot.InlineKeyboardButton{{
        {Text: "Tap", CallbackData: "act:1"},
    }}}})

// gotd/td (MTProto)
sender.Answer(cq, "tapped").NoAlert().Do(ctx)
// buttons via message.RequestBuilder Rows/Button builders
```

## 10. UX rules for bots

1. Menus → inline keyboards attached to a single editable message. Never re-send the menu each time.
2. Constrained input → reply keyboard with `one_time_keyboard=True` + `resize_keyboard=True`, remove after.
3. Confirm destructive actions with an inline "Are you sure?" step.
4. Deep-link into menus: `t.me/mybot?start=open_settings`, parse in `/start`.
5. Give every async action a `send_chat_action` indicator.
6. Limit message edits to ~1/sec per chat; batch UI updates.
7. Use `tg-spoiler` for spoilers, `expandable` quotes for long text — never split walls of text into multiple messages unless needed.
8. Register command descriptions so autocomplete shows them (`set_my_commands`).
9. Localize button labels per user language when i18n is in scope.
10. Keep `callback_data` compact and versioned (`v1:action:id`) — 64-byte hard limit.
