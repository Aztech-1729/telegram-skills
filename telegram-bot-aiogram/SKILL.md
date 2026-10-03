---
name: |
  telegram-bot-aiogram
description: |
  Load this skill to build a Telegram bot using aiogram 3.x. Full reference: Bot, Dispatcher, Routers, magic filters (F), custom filters, middlewares, FSM (Finite State Machine with StatesGroup/FSMContext), DI (dependency injection), i18n, webhooks with aiohttp, and production patterns with complete examples.
---

# aiogram 3.x — Complete Build Guide

## 1. Install

```bash
pip install aiogram                    # core
pip install "aiogram[fastapi]"         # FastAPI webhook integration (optional)
pip install "aiogram[redis]"          # Redis FSM storage (optional)
pip install "aiogram[i18n]"           # babel-based i18n (optional)
```

aiogram 3 (current 3.30+) supports Bot API up to 10.x (10.2/10.3 support landed in recent releases), requires Python 3.10+, fully async (asyncio + aiohttp), magic-filter based. Docs: https://docs.aiogram.dev

## 2. Minimal echo bot

```python
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

async def start_handler(message: Message):
    await message.answer(f"Hello, <b>{message.from_user.full_name}</b>!")

async def echo_handler(message: Message):
    await message.answer(message.text)

async def main():
    bot = Bot(token=TOKEN)   # parse_mode can be set via DefaultBotProperties
    dp = Dispatcher()
    dp.message.register(start_handler, CommandStart())
    dp.message.register(echo_handler, F.text)
    await dp.start_polling(bot)   # handles graceful shutdown

if __name__ == "__main__":
    asyncio.run(main())
```

Bot with defaults:

```python
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
```

## 3. Dispatcher and Routers — modular architecture

`Dispatcher` is itself a router; nest `Router` objects for modularity:

```python
# routers/start.py
from aiogram import Router
router = Router(name="start")

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Welcome!")
```

```python
# main.py
from aiogram import Bot, Dispatcher
from routers import start, admin, callbacks

dp = Dispatcher()
dp.include_routers(start.router, callbacks.router, admin.router)  # ORDER MATTERS

async def main():
    await dp.start_polling(Bot(token=TOKEN), allowed_updates=["message", "callback_query"])
```

Observation routers: `dp.message`, `dp.callback_query`, `dp.inline_query`, `dp.edited_message`, `dp.chat_member`, `dp.my_chat_member`, `dp.chat_join_request`, `dp.pre_checkout_query`, `dp.shipping_query`, `dp.poll`, `dp.poll_answer`, `dp.business_message`, `dp.chosen_inline_result`.

Registration styles: decorator `@router.message(filters...)` or explicit `.register(callback, *filters)`. First matching handler wins per event.

## 4. Magic filter (F) and filters — the aiogram superpower

```python
from aiogram.filters import Command, CommandObject, CommandStart, CommandHelp
from aiogram.filters.callback_data import CallbackData
from aiogram import F
```

Magic filter examples:

```python
@router.message(F.text.lower() == "hello")
@router.message(F.text.startswith("/track"))
@router.message(F.photo)                                   # any photo
@router.message(F.photo[-1].file_id)                       # truthy check
@router.message(F.document.mime_type == "application/pdf")
@router.message(F.chat.type == "private")
@router.message(F.chat.type.in_({"group", "supergroup"}))
@router.message(F.from_user.id == 123456)
@router.message(F.from_user.id.in_(ADMIN_IDS))
@router.message(F.text.regexp(r"^\d{4}$"))
@router.message(F.reply_to_message.from_user.is_bot)
@router.message(F.forward_from)
@router.callback_query(F.data == "menu:close")
@router.callback_query(F.data.startswith("page:"))
```

Combining: `F.text & ~F.photo`, `F.text.lower() == "hi" | F.text.lower() == "hey"`.

Command filters:

```python
from aiogram.filters import Command
from aiogram.types import Message

@router.message(Command("remind"))     # matches /remind and /remind@YourBot
async def remind(message: Message, command: Command):   # magic DI — command injected
    args = command.args          # full text after the command
    await message.answer(f"Args: {command.args}")
```

`CommandStart(deep_link=True)` parses deep-link payloads: `command.args` holds the `start` parameter.

Custom filter class:

```python
from aiogram.filters import Filter

class IsAdmin(Filter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")

@router.message(IsAdmin(), Command("ban"))
async def ban(message: Message): ...
```

## 5. CallbackData — typed, safe callback payloads

```python
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

class PageCB(CallbackData, prefix="page"):
    action: str      # e.g. "open" / "close"
    page: int
    item_id: str | None = None

def page_kb(page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Page {page+1}", callback_data=PageCB(action="open", page=page).pack())],
        [InlineKeyboardButton(text="❌", callback_data=PageCB(action="close", page=page).pack())],
    ])

@router.callback_query(PageCB.filter())
async def on_page(cb: CallbackQuery, callback_data: PageCB):   # auto-parsed and injected
    if callback_data.action == "close":
        await cb.message.delete()
    else:
        await cb.message.edit_text(f"Page {callback_data.page}", reply_markup=page_kb(callback_data.page + 1))
    await cb.answer()   # ALWAYS answer
```

`pack()` serializes into ≤64 bytes; `filter()` unpacks with type validation. This replaces fragile string parsing.

## 6. FSM — multi-step dialogs (built-in, first-class)

```python
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

class Form(StatesGroup):
    name = State()
    age = State()
    language = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer("What's your name?", reply_markup=ReplyKeyboardRemove())

@router.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=html.quote(message.text))
    await state.set_state(Form.age)
    await message.answer(
        "Nice! Did you like bots?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Yes"), KeyboardButton(text="No")]],
            resize_keyboard=True, one_time_keyboard=True,
        ),
    )

@router.message(Form.age, F.text.regexp(r"^\d+$"))
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=int(message.text))
    data = await state.get_data()
    await state.clear()      # ALWAYS clear at the end
    await message.answer(f"Summary: {data}", reply_markup=ReplyKeyboardRemove())

@router.message(Form.age)
async def bad_age(message: Message, state: FSMContext):
    await message.reply("Please send digits only.")

@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        return
    await state.clear()
    await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())
```

FSM API: `state.set_state(...)`, `await state.update_data(**kv)`, `await state.get_data()`, `await state.set_data({...})`, `await state.clear()`. States survive per user+chat in memory by default; **change storage** for production:

```python
from aiogram.fsm.storage.redis import RedisStorage   # requires aiogram[redis]
dp = Dispatcher(storage=RedisStorage.from_url("redis://localhost:6379/0"))
```

FSM works in filters too: `@router.message(Form.name)` only matches when the user is in that state. Use `StateFilter(None)` for "no state".

## 7. Dependency injection (DI)

aiogram 3 injects values by parameter NAME — use this instead of global variables:

```python
async def handler(
    message: Message,          # the event
    bot: Bot,                  # current bot
    state: FSMContext,         # current FSM context
    command: Command,          # if Command filter used
    event_from_user: User,     # user (even for callback queries)
    event_chat: Chat,          # chat
    dispatcher: Dispatcher,
): ...
```

Middlewares inject custom context data:

```python
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any, Awaitable, Callable, Dict

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            data["session"] = session
            return await handler(event, data)

dp.update.middleware(DbSessionMiddleware(pool))
# then handlers can declare: async def h(message: Message, session): ...
```

Middleware types: outer (`dp.update.outer_middleware`) runs for all events before routing; inner runs within a specific observation. Middlewares can short-circuit (return without calling handler) — perfect for throttling/auth:

```python
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate = rate_limit
        self.last_call: dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user:
            now = asyncio.get_event_loop().time()
            if now - self.last_call.get(user.id, 0) < self.rate:
                return None      # silently drop
            self.last_call[user.id] = now
        return await handler(event, data)
```

## 8. Sending, editing, media

```python
await message.answer("text")                        # reply in same chat
await message.reply("text")                         # with reply-to
await message.answer_photo(FSInputFile("cat.jpg"), caption="<b>Cat</b>")
await message.answer_document(FSInputFile("report.pdf"))
await bot.send_message(chat_id, "Direct send")

# download incoming media
file = await bot.get_file(message.photo[-1].file_id)
await bot.download_file(file.file_path, "photo.jpg")
# or: await bot.download(message.photo[-1], destination="photo.jpg")

# edit
await message.edit_text("Edited")
await cb.edit_text("Edited from callback")
await cb.message.edit_reply_markup(reply_markup=None)

# albums — use MediaGroupBuilder
from aiogram.utils.media_group import MediaGroupBuilder
album = MediaGroupBuilder(caption="<b>My album</b>")
album.add_photo("https://example.com/1.jpg")
album.add_photo(FSInputFile("2.jpg"))
await message.answer_media_group(media=album.build())
```

`FSInputFile` is the object for local files/bytes; URLs are passed as plain strings.

## 9. Webhooks with aiohttp (or FastAPI)

```python
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

async def on_startup(bot: Bot):
    await bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}", secret_token=SECRET, drop_pending_updates=True)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_routers(...)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=SECRET).register(app, path=f"/{TOKEN}")
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)
    web.run_app(app, host="0.0.0.0", port=8443)
```

Bot API limits: HTTPS required, ports 443/80/88/8443. For local dev use polling (`start_polling`) — never both.

## 10. Scheduled tasks

aiogram does not ship a scheduler; use APScheduler:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(daily_post, "cron", hour=9, minute=0, args=[bot])
    scheduler.add_job(weekly_report, "interval", weeks=1, args=[bot])
    scheduler.start()
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
```

## 11. i18n

```python
from aiogram.utils.i18n import I18n, SimpleI18nMiddleware
# locales/en/LC_MESSAGES/bot.po (+ compiled .mo)

i18n = I18n(path="locales", default_locale="en")
dp.update.outer_middleware(SimpleI18nMiddleware(i18n))

from aiogram.utils.i18n import gettext as _
@router.message(CommandStart())
async def start(message: Message):
    await message.answer(_("Welcome!"))
```

## 12. Error handling

```python
from aiogram import Bot
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

@dp.error()
async def on_error(event: ErrorEvent):
    exc = event.exception
    logging.exception("Update caused error", exc_info=exc)
    if isinstance(exc, TelegramRetryAfter):
        await asyncio.sleep(exc.retry_after)
    if isinstance(exc, TelegramForbiddenError):
        pass  # user blocked the bot — stop messaging them
    return True   # handled; True = stop propagation
```

## 13. Full production layout

```
bot/
├── main.py
├── config.py
├── filters/__init__.py
├── handlers/
│   ├── user.py        # router = Router(name="user")
│   ├── admin.py
│   └── callbacks.py
├── keyboards/
│   └── inline.py      # builders + CallbackData classes
├── middlewares/
│   ├── throttling.py
│   └── db.py
├── states/
│   └── form.py        # StatesGroup definitions
└── services/
    └── database.py
```

```python
# main.py
dp = Dispatcher(storage=RedisStorage.from_url(REDIS_URL))
dp.include_routers(handlers.user.router, handlers.callbacks.router, handlers.admin.router)
dp.update.middleware(ThrottlingMiddleware())
dp.update.middleware(DbSessionMiddleware(pool))
dp.error.register(on_error)
```

## 14. aiogram vs PTB — choosing

- Both are excellent; aiogram 3 leads on: FSM first-class, magic filters, DI by parameter name, CallbackData typing, native routers.
- PTB leads on: JobQueue built-in, ConversationHandler, huge ecosystem/wiki, sync-style ergonomics.
- If the user didn't specify, prefer aiogram 3 for new FSM-heavy bots, PTB when they mention it or already have PTB code.

## 15. Pre-ship checklist (aiogram)

- [ ] `await cb.answer()` in every callback handler
- [ ] `state.clear()` at the end of every FSM flow
- [ ] Redis storage for FSM in multi-worker deployments
- [ ] Router include order: specific → generic
- [ ] Throttling middleware registered
- [ ] `allowed_updates` set explicitly on polling/webhook
- [ ] Error handler registered with `@dp.error()`
- [ ] Token in env; `.session`/`.env` gitignored
- [ ] HTML escape on user input (`html.quote`)
- [ ] Commands registered via `bot.set_my_commands`
