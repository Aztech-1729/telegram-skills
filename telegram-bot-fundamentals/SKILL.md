---
name: |
  telegram-bot-fundamentals
description: |
  Load this skill FIRST for any Telegram bot task. Covers Bot API fundamentals, bot creation via @BotFather, tokens, api_id/api_hash, HTTP endpoints, update types, chat types, rate limits, project scaffolding, security rules, and choosing between Bot API (HTTP) vs MTProto (Telethon) before any library-specific work.
---

# Telegram Bot Fundamentals (Library-Agnostic)

Use this skill as the entry point for every Telegram bot build. Read it fully before writing any bot code.

## 1. The two ways to talk to Telegram

1. **HTTP Bot API** (`https://api.telegram.org/bot<TOKEN>/<method>`) — official, simple, works everywhere. Libraries: python-telegram-bot (PTB), aiogram, grammY, Telegraf, ngrok for local webhooks.
2. **MTProto** — Telegram's native protocol. Direct socket connection, no polling/webhooks, access to nearly the full Telegram API including user-account features. Python library: **Telethon**.

Decision rules:
- Bots only, standard features (messages, keyboards, inline, payments, Mini Apps) → HTTP Bot API with PTB or aiogram.
- Need user-account actions (reading arbitrary chats, scraping, advanced admin work, features Bot API lacks) → Telethon.
- Never mix both in one file without reason; pick one architecture per project.

## 2. Creating a bot

1. Open Telegram, search **@BotFather**, send `/newbot`.
2. Choose a display name and a username (must end in `bot`, e.g. `myhelper_bot`).
3. BotFather returns a **token** like `123456789:AAE-xxxxxxxxxxxxxxxxxxxxxxxxxxxx`. Treat it like a password.
4. Useful BotFather commands: `/setcommands` (register command menu), `/setdescription`, `/setabouttext`, `/setuserpic`, `/setprivacy` (privacy mode), `/setinline` (enable inline mode), `/mybots` (manage all bots), `/token` (revoke/rotate).

**Privacy mode**: ON by default in groups — the bot only receives commands, replies to itself, and service messages. Use `client.set_my_commands(...)` with `BotCommandScopeAllGroupChats` or disable privacy via `/setprivacy` if the bot must see all group messages.

**api_id / api_hash** (only needed for MTProto/Telethon): get from https://my.telegram.org → API Development. Not needed for HTTP Bot API.

## 3. Core Bot API concepts (version 10.x as of late 2026)

- **Updates**: the bot receives `Update` objects via long polling (`getUpdates`) or webhook (`setWebhook`). Update kinds: `message`, `edited_message`, `channel_post`, `callback_query`, `inline_query`, `chosen_inline_result`, `my_chat_member`, `chat_member`, `chat_join_request`, `poll_answer`, `pre_checkout_query`, `shipping_query`, `business_message`, etc.
- **Chat types**: `private`, `group`, `supergroup`, `channel`.
- **Entities**: messages carry text plus `MessageEntity` objects (bold, links, mentions, code...). Send formatted text with parse mode `HTML` (preferred) or `MarkdownV2` (escape needed: `_ * [ ] ( ) ~ ` > # + - = | { } . !`).
- **Files**: send by `file_id` (fast, reuse), HTTP URL, or multipart upload. Bot API files limited to **20 MB download / 50 MB upload** (20 MB for photos/animated stickers as file). Larger files require MTProto (Telethon — 2 GB by default, 4 GB premium).
- **Message length limit**: 1–4096 characters after entity parsing.

### Common methods (all `snake_case` HTTP endpoints)
Messaging: `send_message`, `send_photo`, `send_audio`, `send_document`, `send_video`, `send_animation`, `send_voice`, `send_video_note`, `send_media_group`, `send_location`, `send_venue`, `send_contact`, `send_poll`, `send_dice`, `send_chat_action`, `edit_message_text`, `edit_message_media`, `edit_message_reply_markup`, `delete_message`, `forward_message`, `copy_message`, `set_message_reaction`, `send_checklist`.
Chat: `get_chat`, `get_chat_member`, `get_chat_administrators`, `ban_chat_member`, `unban_chat_member`, `restrict_chat_member`, `promote_chat_member`, `set_chat_title`, `set_chat_photo`, `pin_chat_message`, `unpin_chat_message`, `create_chat_invite_link`, `set_chat_permissions`.
Bot itself: `get_me`, `get_my_commands`, `set_my_commands`, `log_out`, `close`, `get_star_transactions`, `get_user_gifts`, `get_chat_gifts`.
Payments: `send_invoice`, `create_invoice_link`, `answer_pre_checkout_query`, `answer_shipping_query`, `refund_star_payment`, `send_gift`, `gift_premium_subscription`.
Web Apps / Mini Apps: `answer_web_app_query`, plus `WebApp initData` validation (HMAC — see the payments skill).

## 4. Sending a request with curl (no library)

```bash
TOKEN="123:AAE..."
# Get bot info
curl "https://api.telegram.org/bot$TOKEN/getMe"
# Send a message (HTML parse mode)
curl -d "chat_id=987654321" \
     -d "text=<b>Hello!</b> Click: <a href='https://example.com'>site</a>" \
     -d "parse_mode=HTML" \
     "https://api.telegram.org/bot$TOKEN/sendMessage"
# Upload a file
curl -F "chat_id=987654321" -F "photo=@photo.jpg" \
     "https://api.telegram.org/bot$TOKEN/sendPhoto"
```

Poll updates manually:

```bash
curl "https://api.telegram.org/bot$TOKEN/getUpdates?offset=-1"
```

`offset` = last received `update_id + 1` confirms the update and fetches the next ones.

## 5. Rate limits and limits (critical for production)

- Free broadcast limit: **30 messages/second** overall, ~1 message/second per chat, ~20 messages/minute to the same group. Above the free 30/s, each extra message **costs 0.1 Stars from the bot's balance** — and the bot must hold **at least 10,000 Stars** to use paid broadcasting.
- Bulk notifications: send to max ~30 different chats per second; sleep 1s every 20-30 sends and retry on HTTP 429 honoring `retry_after` in `parameters`.
- Global payload limit 30 KB for inline keyboards; 64 callbacks/second per bot; album (`send_media_group`) = 2–10 items.
- getUpdates timeout max 50 seconds.
- Files: **20 MB download / 50 MB upload** via Bot API (the `file_size` field now exceeds signed 32-bit — 4 GB premium uploads exist on MTProto).
- Bot API method names are case-insensitive.

Always implement 429 handling with backoff.

## 6. Security rules (non-negotiable)

1. Never hardcode the token. Use environment variables (`TELEGRAM_BOT_TOKEN`) or a secret manager.
2. For webhooks, use a long random URL path (`https://api.example.com/bot/hook/<64-hex-chars>`) — Telegram supports ports 443, 80, 88, 8443 with a valid TLS cert or self-signed cert uploaded.
3. Validate `X-Telegram-Bot-Api-Secret-Token` header on webhook requests (`set_webhook(secret_token=...)`) and reject anything that does not match.
4. A token in a leaked repo must be revoked via `/revoke` in BotFather immediately.
5. Never trust client-supplied data — always re-validate with the API (e.g., check `get_chat_member` for admin rights instead of trusting a callback payload).
6. Escape user input when echoing it with HTML parse mode (`html.escape` in Python).

## 7. Project scaffolding template (Python)

```
mybot/
├── .env                  # TELEGRAM_BOT_TOKEN=... (never commit)
├── .gitignore            # .env, *.session, __pycache__/
├── requirements.txt      # python-telegram-bot[job-queue] OR aiogram OR telethon
├── main.py               # entrypoint: builds app, registers handlers, runs
├── config.py             # loads env vars
├── handlers/
│   ├── __init__.py
│   ├── start.py          # /start, /help
│   ├── admin.py          # admin-only commands
│   └── callbacks.py      # inline keyboard callbacks
├── keyboards/            # reply/inline keyboard builders
├── services/             # business logic, DB calls, external APIs
└── middlewares/          # throttling, logging, auth
```

`config.py` pattern:

```python
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]   # fail fast if missing
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x}
DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
ENV = os.environ.get("ENV", "prod")
```

## 8. Update routing decision table (for any library)

| User action | Update type | Typical handling |
|---|---|---|
| `/command` | `message` with text starting `/` | command handler |
| Tap inline button | `callback_query` | `answer_callback_query` + act |
| Type `@bot query` in any chat | `inline_query` | `answer_inline_query` with results |
| Choose from reply keyboard | `message` | state machine / filter on text |
| Join request | `chat_join_request` | approve/decline |
| Member promoted/banned | `chat_member` | audit log |
| Bot added/removed | `my_chat_member` | enable/disable per-chat state |
| Buy via Stars | `pre_checkout_query` → successful_payment message | answer pre-checkout then deliver |

## 9. Common pitfalls checklist

- Forgetting `await` on send calls (async libraries) — message never goes out.
- Not calling `answer_callback_query` → user sees a spinner forever.
- Using `MarkdownV2` without escaping → `Bad Request: can't parse entities`.
- Assuming `update.message` always exists (it can be `callback_query`, `edited_message`, etc.).
- Ignoring 429 rate limits in broadcast loops.
- Storing per-user state in globals instead of FSM/persistence → wrong data across users.
- Sending files >50 MB via Bot API (must use MTProto upload or stream via URL).
- Polling and webhook at the same time (getUpdates blocks while a webhook is set).

## 9.5 Latest Bot API capabilities you should know (2025–2026, through 10.x)

- **Rich Messages (Bot API 10.1–10.3)** — `sendRichMessage` with structured **Rich Blocks**: slideshow (`InputRichBlockSlideshow`), collage (`InputRichBlockCollage`), tables, headings, quotations, collapsible details, media blocks, and (10.3) **buttons inside rich messages**; bots can **stream AI-generated replies with seamless rich formatting**.
- **AI streaming drafts (10.x)** — `sendMessageDraft` / `sendRichMessageDraft` for temporary streamed AI replies in private chats; official guide: core.telegram.org/api/bots/ai.
- **Private-chat topics** — forum topics in private bot chats when Threaded mode is enabled; **Channel Direct Messages** (DM topics in channels); **suggested posts** in channels.
- **Ephemeral messages (10.2)** — full edit/delete method set; `EphemeralMessageParameters.replace_callback_query_message` shows an ephemeral message in place of the original. **Communities** — new linked channel/group/bot topology.
- **Message streaming** — every bot can now stream long AI-style answers progressively (edit a message as content arrives; throttle edits ~1/s to avoid 429) — enabled for all bots since March 2026.
- **Checklists** — native to-do lists: `send_checklist`, mark/checklist-task service messages, `reply_to_checklist_task_id`, `completed_by_chat` on tasks, date/time entities in titles.
- **Gifts & Stars** — send gifts, gift Premium paid in Stars, `get_star_transactions`, `get_user_gifts`, `get_chat_gifts`, unique-gift upgrades, `unique_gift_colors` on `ChatFullInfo`, gift publisher attribution.
- **Access whitelists** — granular per-bot user whitelists via @BotFather; manager bots set them via API.
- **Story areas** — weather areas (up to 3/story), unique-gift areas, expanded entities in quotes/gift texts.
- **Mini App hardening** — Mini App methods are origin-restricted to the registered domain (enforced for all apps since July 20, 2026; opt-out via the BotFather Mini App settings).
- **Service messages** — bots handle chat-owner leave/ownership-change service messages; bots can fetch recent messages pinned to a user's profile; video objects expose available qualities.
- **copy_text buttons** — inline buttons that copy text to the user's clipboard.
- Always check the changelog (core.telegram.org/bots/api-changelog) before relying on a niche feature — Telegram ships updates roughly monthly.

## 10. Next steps inside this skill set

- Building with **python-telegram-bot** → load skill `telegram-bot-python-telegram-bot`.
- Building with **aiogram** → load skill `telegram-bot-aiogram`.
- MTProto / userbot / big files → load skill `telegram-bot-telethon`.
- Keyboards, media, formatting → `telegram-bot-keyboards-ui`.
- Payments/Stars/Mini Apps → `telegram-bot-payments-stars`.
- FSM, jobs, persistence, webhooks, deployment → `telegram-bot-advanced-features`.
- Ready-made complete bot implementations → `telegram-bot-recipes`.
- Building in **Go**: HTTP Bot API → `telegram-bot-go-botapi`; MTProto (TDLib parity) → `telegram-bot-gotd`; production helpers (sessions, flood-wait, rate limiting, observability) → `telegram-bot-gotd-contrib`.
- Building a web app inside Telegram → `telegram-bot-miniapps`.
- Pro message/UI design: Rich Messages, shop storefront layouts, formatting, streaming answers → `telegram-bot-rich-messaging`.
- Monetization (Stars invoices, gifts, Premium gifting) → `telegram-bot-payments-stars`.

Language/library decision matrix (global):

| Need | Python | Go |
|---|---|---|
| Simple HTTP bot, fast iteration | PTB or aiogram | go-telegram/bot or gotgbot |
| FSM-heavy dialogs | aiogram 3 | go-telegram/bot + own state |
| Userbot / MTProto | Telethon | gotd/td (+contrib) |
| 2 GB files, raw API | Telethon | gotd/td |
| Cron jobs / scheduling | PTB JobQueue / APScheduler | robfig/cron with any Go lib |
| Extreme concurrency | aiogram (asyncio) | Go frameworks (goroutines native) |
