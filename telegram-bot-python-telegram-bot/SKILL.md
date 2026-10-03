---
name: |
  telegram-bot-python-telegram-bot
description: |
  Load this skill to build a Telegram bot using python-telegram-bot (PTB) v22+. Full reference: Application/ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, filters, JobQueue, Persistence, ConversationHandler, error handlers, webhooks, and production-grade code patterns with complete examples.
---

# python-telegram-bot (PTB) v22 — Complete Build Guide

## 1. Install and versions

```bash
pip install "python-telegram-bot[job-queue]"   # with APScheduler-based JobQueue
pip install "python-telegram-bot[rate-limiter]"  # optional AIORateLimiter
```

- PTB v22.8 supports Bot API up to 10.0; requires Python 3.10+. Fully async (asyncio) since v20. Upgrade with `pip install -U python-telegram-bot` — releases track Bot API fast (v22.7 → API 9.4/9.5, v22.8 → 9.6/10.0).
- Docs: https://docs.python-telegram-bot.org — check the changelog page for Bot API support status.

## 2. Minimal echo bot

```python
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Hi {update.effective_user.first_name}! I echo everything."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(update.message.text)

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()   # handles startup, shutdown, and graceful Ctrl+C

if __name__ == "__main__":
    main()
```

## 3. Application — building and configuring

```python
from telegram.ext import Application, AIORateLimiter, Defaults
from telegram.constants import ParseMode

app = (
    Application.builder()
    .token(TOKEN)
    .defaults(Defaults(parse_mode=ParseMode.HTML))  # default HTML everywhere
    .rate_limiter(AIORateLimiter(max_retries=3))     # auto-retry on 429
    .concurrent_updates(True)                        # process updates in parallel
    .build()
)
```

Key builder options: `.token()`, `.base_url()`/`.base_file_url()` (local Bot API server), `.concurrent_updates(256)` (max concurrent tasks), `.job_queue(...)`, `.persistence(...)`, `.context_types(...)` for custom `bot_data` types, `.secret_token()` for webhook validation, `.connect_timeout(30)`/`.read_timeout(30)`/`.write_timeout(30)` (network timeouts), `.get_updates_read_timeout(42)` (polling timeout, must exceed long-poll interval), `.http_version('1.1')`.

Lifetime: `app.run_polling()` internally runs `asyncio.run()`; register `post_init`, `post_shutdown`, `post_stop`:

```python
async def post_init(app: Application):
    await app.bot.set_my_commands([
        ("start", "Start the bot"),
        ("help", "Show help"),
        ("settings", "Open settings"),
    ])

app = Application.builder().token(TOKEN).post_init(post_init).build()
```

## 4. Handlers — the complete set

```python
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ChosenInlineResultHandler,
    ConversationHandler, ChatMemberHandler, ChatJoinRequestHandler,
    ShippingQueryHandler, PreCheckoutQueryHandler, PollAnswerHandler,
    TypeHandler, ApplicationHandlerStop,
)
```

- `CommandHandler("start", cb)` — also accepts a list `["start", "hi"]`; `filters` arg for extra checks.
- `MessageHandler(filters.TEXT & ~filters.COMMAND, cb)`.
- `CallbackQueryHandler(cb, pattern=...)` — pattern is a regex matched against `callback_data`, or `filters.CallbackQuery`.
- `InlineQueryHandler(cb)`, `ChosenInlineResultHandler(cb)`.
- `ChatMemberHandler(cb, ChatMemberHandler.CHAT_MEMBER | MY_CHAT_MEMBER)`.
- `PreCheckoutQueryHandler(cb)`, `ShippingQueryHandler(cb)` — payments.
- `TypeHandler(Update, cb)` — catch-all for any update.
- Group ordering: `app.add_handler(h, group=0)` — groups run sequentially, handlers in the same group run first-match-wins. Use `ApplicationHandlerStop` to stop further groups.

Handler registration order matters inside a group; put specific handlers before generic ones.

### Filters cheat sheet

```python
filters.TEXT, filters.CAPTION, filters.PHOTO, filters.VIDEO, filters.Document.ALL,
filters.Document.MimeType("application/pdf"), filters.AUDIO, filters.VOICE,
filters.Sticker.ALL, filters.LOCATION, filters.CONTACT, filters.COMMAND,
filters.REPLY, filters.FORWARDED, filters.ViaBot("some_bot"), filters.Entity("url"),
filters.ChatType.PRIVATE, filters.ChatType.GROUPS,
filters.Chat(chat_id=-100123), filters.User(user_id=123), filters.StatusFilter.ADMIN,
filters.Regex(r"^track\s+(\w+)$"),
filters.UpdateType.MESSAGE
# combine with & and ~
```

## 5. ContextTypes and Context object — the agent's toolkit

Inside handlers, `context` (`ContextTypes.DEFAULT_TYPE`) carries everything:

- `context.bot` — the `Bot` instance; every API method is async.
- `context.args` — parsed command arguments (list of words).
- `context.chat_data`, `context.user_data` — per-chat/per-user dicts (persisted if persistence enabled).
- `context.bot_data` — global dict.
- `context.job_queue` — schedule jobs.
- `context.application`, `context.update`.

```python
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /remind 30 Buy milk"""
    try:
        minutes = float(context.args[0])
        text = " ".join(context.args[1:]) or "⏰ Reminder!"
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /remind <minutes> <text>")
        return
    context.job_queue.run_once(
        remind_job, when=minutes, chat_id=update.effective_chat.id, data=text,
        name=f"remind_{update.effective_user.id}",
    )
    await update.message.reply_text(f"I'll remind you in {minutes:.0f} min.")

async def remind_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    await context.bot.send_message(job.chat_id, f"⏰ {job.data}")
```

## 6. Sending messages and media

```python
await context.bot.send_message(chat_id, "<b>HTML</b> formatted text")
await context.bot.send_photo(chat_id, photo=open("cat.jpg", "rb"), caption="Photo of a cat")

# Send from handler with a shortcut
await update.message.reply_text(...)                       # same chat
await update.message.reply_photo(open("p.png", "rb"), caption="Banner")

# Editing
await context.bot.edit_message_text("New text", chat_id, message_id, reply_markup=None)
await query.edit_message_text("Edited via callback query")          # CallbackQuery shortcut
await query.edit_message_reply_markup(reply_markup=None)            # remove keyboard

# Deleting, pinning
await context.bot.delete_message(chat_id, message_id)
await context.bot.pin_chat_message(chat_id, message_id, disable_notification=False)

# Copy/forward
await update.message.forward(chat_id=channel_id)
await update.message.copy(chat_id=channel_id)

# Album upload
from telegram import InputMediaPhoto
await context.bot.send_media_group(chat_id, [
    InputMediaPhoto("https://cdn.example.com/1.jpg", caption="Album 1"),
    InputMediaPhoto(open("2.jpg", "rb")),
])

# React to a message
await update.message.set_reaction("👍")  # emoji as ReactionTypeEmoji

# Send a file the user sent earlier — keep the file_id
file_id = update.message.photo[-1].file_id          # highest resolution
await context.bot.send_photo(chat_id, file_id)      # reuse is instant
```

Downloading:

```python
tg_file = await update.message.document.get_file()
await tg_file.download_to_drive("local_copy.pdf")
# Note: 20 MB limit via Bot API. Bigger → Telethon or a local Bot API server.
```

## 7. Callback queries — full flow

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MENU_TEXT = "What do you want to do?"

def build_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 List items", callback_data="list:0")],
        [
            InlineKeyboardButton("◀️", callback_data="list:0"),
            InlineKeyboardButton("▶️", callback_data="list:1"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="menu:close")],
    ])

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MENU_TEXT, reply_markup=build_menu())

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Loading...")   # ALWAYS answer, or the button spins forever
    action, page = query.data.split(":")
    if action == "menu" and page == "close":
        await query.message.delete()
    elif action == "list":
        await query.edit_message_text(f"Page {page} of results", reply_markup=build_menu())

app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(list|menu):"))
```

Rules: `callback_data` must be ≤64 bytes; the bot must call `query.answer()` for every callback (even `await query.answer()`); use compact encodings (`id:action`) and resolve labels server-side.

## 8. ConversationHandler — multi-step dialogs

```python
from telegram.ext import ConversationHandler

ASK_NAME, ASK_AGE, DONE = range(3)

async def conv_start(update: Update, context):
    await update.message.reply_text("What's your name?")
    return ASK_NAME

async def got_name(update: Update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("How old are you?")
    return ASK_AGE

async def got_age(update: Update, context):
    context.user_data["age"] = update.message.text
    await update.message.reply_text(
        f"Done: {context.user_data['name']}, {context.user_data['age']} years old."
    )
    return ConversationHandler.END

async def cancel(update: Update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("form", conv_start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
        ASK_AGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, got_age),
            CallbackQueryHandler(got_age, pattern="^age:"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
    per_message=False,   # WARNING: per_message=True with CallbackQueryHandler only
)
app.add_handler(conv)
```

Notes: state is kept per (chat, user) key; with persistence it survives restarts. For complex flows prefer explicit state in `chat_data`/DB or a custom state machine — ConversationHandler state lives in memory by default.

## 9. JobQueue — scheduling

```python
jq = app.job_queue
jq.run_once(callback, when=30)                      # 30 seconds
jq.run_repeating(callback, interval=3600, first=10)  # hourly
jq.run_daily(callback, time=time(hour=9, minute=0, tz=pytz.timezone("Asia/Kolkata")))
jq.run_monthly(callback, when=time(hour=0), day=1)
job = jq.run_once(task, when=0, chat_id=cid, name="x", data={...})
job.schedule_removal()
jq.get_jobs_by_name("x")
```

`callback` receives `context` with `context.job.data`, `.chat_id`, `.name`. JobQueue requires the `job-queue` extra (APScheduler). Pass `chat_id=` when scheduling; inside the job use `context.job.chat_id` and `context.bot.send_message(context.job.chat_id, ...)`.

## 10. Persistence — survive restarts

```python
from telegram.ext import PicklePersistence

persistence = PicklePersistence(filepath="bot_data.pkl")   # or custom class
app = Application.builder().token(TOKEN).persistence(persistence).build()
# user_data / chat_data / bot_data and ConversationHandler states are now saved
# flushed on update and on shutdown automatically
```

For production use a custom `BasePersistence` subclass backed by Redis/Postgres, and put business data in a real database (SQLAlchemy async + aiosqlite/asyncpg) rather than bot_data.

## 11. Error handling and admin log

```python
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update %s", update, exc_info=context.error)
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id, f"⚠️ Bot error:\n<code>{html.escape(str(context.error)[:3500])}</code>"
            )
        except Exception:
            pass

app.add_error_handler(error_handler)
```

Also: `ApplicationHandlerStop` stops update processing; in error callbacks `context.error` holds the exception.

## 12. Webhooks (production alternative to polling)

```python
app = Application.builder().token(TOKEN).updater(None).secret_token(SECRET).build()

async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0", port=8443,
        url_path=WEBHOOK_PATH,
        webhook_url=f"https://bot.example.com/{WEBHOOK_PATH}",
        secret_token=SECRET,            # Telegram sends it back in a header
        allowed_updates=["message", "callback_query"],
    )
    await asyncio.Event().wait()        # run forever
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

asyncio.run(main())
```

Simpler one-liner alternative:

```python
app.run_webhook(
    listen="0.0.0.0", port=8443, url_path=WEBHOOK_PATH,
    webhook_url=f"https://bot.example.com/{WEBHOOK_PATH}",
    secret_token=SECRET,
)
```

Use webhook when: container/serverless with stable TLS endpoint, need faster delivery, or multiple instances behind one domain. Use polling for local dev. Never run both.

## 13. Inline queries (requires /setinline in BotFather)

```python
from telegram import InlineQueryResultArticle, InputTextMessageContent

async def inline(update: Update, context):
    results = [
        InlineQueryResultArticle(
            id="1", title="Send 'Hello'",
            input_message_content=InputTextMessageContent("Hello!"),
        ),
    ]
    await update.inline_query.answer(results, cache_time=10, is_personal=True)

app.add_handler(InlineQueryHandler(inline))
```

`answer` must be called within ~10 seconds. Use `switch_pm_text`/pagination `next_offset` for long lists.

## 14. Admin and group management example

```python
from telegram import ChatPermissions

async def check_admin(update: Update, context) -> bool:
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")

async def mute(update: Update, context):
    if not await check_admin(update, context):
        await update.message.reply_text("Admins only.")
        return
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        return await update.message.reply_text("Reply to the user to mute.")
    until = datetime.now() + timedelta(minutes=10)
    await context.bot.restrict_chat_member(
        update.effective_chat.id, target.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    await update.message.reply_text(f"Muted {target.mention_html()} for 10 min.")
```

`get_chat_administrators()` returns the full admin list; `promote_chat_member` can promote (with explicit permission flags); `ban_chat_member` with `until_date` for temporary bans.

## 15. Utilities worth knowing

```python
from telegram.helpers import escape_markdown, mention_html, create_deep_linked_url
from telegram.constants import ParseMode, ChatAction

escape_markdown("*text*", version=2)          # escape MarkdownV2
create_deep_linked_url(bot_username, "payload") # https://t.me/mybot?start=payload
# In /start handler read: context.args[0] → "payload"
await update.message.chat.send_action(ChatAction.TYPING)   # typing indicator
from telegram.error import BadRequest, Forbidden, TimedOut, NetworkError, RetryAfter
# Forbidden = bot blocked/kicked — stop messaging that user
# RetryAfter has .retry_after — wait that long, then retry
```

Deep links: `t.me/mybot?start=payload` (payload must be A-Z, a-z, 0-9, `_`, `-`, ≤64 chars); for groups: `t.me/mybot?startgroup=payload`.

## 16. Standard project layout (PTB)

```
bot/
├── main.py               # build Application, import handlers, run
├── config.py             # env tokens, admin IDs
├── handlers/
│   ├── __init__.py       # setup() registers all handlers on app
│   ├── start.py
│   └── buttons.py
├── keyboards/__init__.py
├── services/database.py
└── middlewares.py
```

`handlers/__init__.py` pattern:

```python
from telegram.ext import Application

def setup(app: Application):
    from . import start, buttons
    start.register(app)
    buttons.register(app)
```

Each handler module:

```python
async def cmd_start(update, context): ...
def register(app):
    app.add_handler(CommandHandler("start", cmd_start))
```

## 17. Async performance — never block the event loop

One process = one event loop; ANY blocking call in a handler freezes ALL updates, not just that user's.

```python
# ❌ BAD — blocks the loop
await update.message.reply_photo(open("big.jpg", "rb"))
time.sleep(2)
data = requests.get("https://api.example.com").json()

# ✅ GOOD — async equivalents
import aiofiles, aiohttp

async with aiofiles.open("big.jpg", "rb") as f:
    await update.message.reply_photo(f)
await asyncio.sleep(2)
async with aiohttp.ClientSession() as s:
    async with s.get("https://api.example.com") as r:
        data = await r.json()

# ✅ Sync-only library? Push it to a thread via run_in_executor:
data = await asyncio.get_running_loop().run_in_executor(None, lambda: sync_cpu_work(x))
# (in handlers: context.application.create_task(...), asyncio.to_thread(sync_fn))
```

**Sync SQLite in async bots**: plain `sqlite3` calls block the loop. Use `aiosqlite` (or SQLAlchemy async engine — see the advanced-features skill). For a few quick queries per handler it's tolerable; under load it's a bottleneck — go async.

**Speed checklist (maximum fast):**
- [ ] `concurrent_updates(True)` (or a number ≥ expected concurrent chats) — updates processed in parallel
- [ ] No blocking I/O in handlers: aiofiles/aiohttp/httpx/aiosqlite, or `asyncio.to_thread`
- [ ] HTTP client created once (module/app level), reused across handlers — never per-request `ClientSession`
- [ ] `AIORateLimiter` so 429s retry automatically instead of failing
- [ ] `Defaults(parse_mode=HTML)` to avoid per-call overhead/mistakes
- [ ] Slow external APIs → `await` them (never fire-and-forget) and show a typing indicator
- [ ] Broadcasts: `asyncio.gather` in small batches + sleeps (see advanced-features §4)
- [ ] Heavier CPU work (parsing, ML) → offload to a task queue (celery/arq) and reply when done

## 18. Checklist before shipping a PTB bot

- [ ] Token from env, never committed
- [ ] All commands registered with `set_my_commands`
- [ ] Every `CallbackQueryHandler` calls `query.answer()`
- [ ] 429 handling: `AIORateLimiter` or try/except `RetryAfter`
- [ ] Error handler logs and reports to admins
- [ ] Persistence enabled if state must survive restarts
- [ ] Admin check on all admin commands
- [ ] HTML parse mode + `html.escape` for user input
- [ ] Graceful shutdown tested (Ctrl+C)
- [ ] Webhook secret token set in production
- [ ] README with deployment steps
