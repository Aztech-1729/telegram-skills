# aiogram 3 implementation guide

Cutoff **2026-10-03**; baseline **3.31.0 / Bot API 10.3**, released **2026-08-26**, Python **3.10+**. [Sources](sources.md) fixes verified scope. The supplied `assets/starter/bot.py` is a complete original polling program. Snippets here are **application patterns** requiring the stated surrounding services/configuration.

Contents: setup/migration; routers and filters; typed callbacks; FSM/storage/isolation; DI/middleware; messages/media; webhooks/lifecycle; scheduling; i18n; errors and tests; state/routing recovery.

## Setup, version boundaries and framework choice

Install `aiogram==3.31.0`; add documented extras only when needed: `[redis]` for Redis FSM, `[i18n]` for gettext/Babel, or other package-listed options. **There is no `[fastapi]` extra** in this release. FastAPI is separately installed and integrated through a request adapter. New projects may use the dated baseline pin; existing projects keep their pin until migration is tested. The starter's `BOT_TOKEN` and optional `REDIS_URL` are local configuration conventions.

aiogram offers native routers, FSM, magic filters, CallbackData and named DI. PTB is also suitable for ordinary bots, particularly existing PTB applications or a requested JobQueue/ConversationHandler architecture; do not impose migration. Telethon addresses different MTProto/user-account needs.

For aiogram 2 migration: Dispatcher no longer takes Bot; replace executor startup with asyncio/polling or explicit webhook lifecycle; use keyword model/method fields; configure HTML/defaults with `DefaultBotProperties`; register explicit content/state filters; use `CommandObject.args` instead of removed `message.get_args`; replace `forward_from` with `forward_origin`. Models can be frozen, optional fields can be None, and callbacks may carry inaccessible messages. Storage-key/state migrations can invalidate live conversations; plan recovery. New 3.31.0 changes include API 10.3 ephemeral-message parameters and fixes to defaults/webhook DI—do not invent signatures for these features from older snippets. [Migration](https://docs.aiogram.dev/en/v3.31.0/migration_2_to_3.html), [release notes](https://docs.aiogram.dev/en/v3.31.0/changelog.html), [package metadata](https://pypi.org/pypi/aiogram/3.31.0/json).

## Dispatcher, Router and filters

Dispatcher is the root Router. Compose separate command, callback, admin and feature routers with `include_router(s)`, keeping specific routes before broad ones. The first successful handler normally ends event propagation. Do not attach the same Router to multiple parents; construct fresh routers for independent applications/tests.

Use event observers (`message`, `callback_query`, `inline_query`, `edited_message`, membership/join requests, shipping/pre-checkout, polls, business updates) rather than dispatching everything manually. `resolve_used_update_types()` helps subscribe to registered events; verify exceptional feature requirements and BotFather settings separately.

Application pattern using a preexisting Router and async handler:

```python
from aiogram import F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

@router.message(Command('remind'))
async def remind(message: Message, command: CommandObject):
    await message.answer(command.args or 'Usage: /remind <minutes> <text>', parse_mode=None)

@router.message((F.text.casefold() == 'hi') | (F.text.casefold() == 'hey'))
async def greet(message: Message):
    await message.answer('Hello')
```

Command parsing injects a **CommandObject**, not the Command filter itself. `CommandStart(deep_link=True)` supplies the start payload through `command.args`; validate/decode it only as the chosen encoding requires. `F.text`, `F.photo`, `F.document.mime_type`, `F.chat.type.in_(...)` and `F.from_user.id` inspect actual content. Parenthesize both sides of an OR comparison. aiogram 3 does not automatically restrict an unfiltered handler to text or empty FSM state: use `StateFilter(None)` where that restriction is needed. `F.forward_origin` replaces old forwarded-message fields.

Custom Filter can return bool or a dictionary of injected values. An admin filter calls `bot.get_chat_member` and checks the relevant status/rights; also check the bot's permission and handle anonymous sender-chat cases. A visible command/menu is not an authorization mechanism. [Router](https://docs.aiogram.dev/en/v3.31.0/dispatcher/router.html), [magic filters](https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/magic_filters.html), [commands](https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/command.html).

## CallbackData and menu lifecycle

Define a CallbackData subclass with a short prefix and typed fields. Build `InlineKeyboardMarkup(inline_keyboard=...)` using keyword fields; `.pack()` encodes, `.filter(...)` parses and injects `callback_data`. Oversized or separator-containing fields raise errors; packing does not silently shorten them. A 64-byte payload cap still applies. Use compact resource IDs and retain trusted state/prices/permissions server-side.

Answer before slow work, validate actor/resource authorization, then edit. `cb.message.edit_text` works only on an accessible Message. For inline messages use `bot.edit_message_text(inline_message_id=...)`; otherwise treat unavailable messages as expired. `cb.edit_text` is not an API. Handle repeated/unchanged edits deliberately and avoid a broad catch that hides lost permissions. For pagination, enforce page bounds and ownership rather than trusting button data. [CallbackData](https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/callback_data.html), [CallbackQuery](https://docs.aiogram.dev/en/v3.31.0/api/types/callback_query.html).

## FSM: transitions, persistence and event isolation

Use `StatesGroup`/`State` to name steps, `FSMContext` to `set_state`, `update_data`, `get_data`, `set_data` and `clear`. Register cancellation/reentry commands before state-wide handlers. Restrict name/age steps to appropriate content; a text name handler must not accept photos or accidentally consume `/cancel`. Validate before transitions. Clear state when the flow finishes/cancels, while leaving durable business records intact. The starter asks for numeric age and validates numeric input rather than presenting contradictory Yes/No buttons.

MemoryStorage is process-local and loses data on stop; it is appropriate for the demonstration. For multiple workers/restart continuity, use RedisStorage or another documented backend plus a deliberate key strategy. Defaults group by user in chat; topic workflows may need a topic-aware FSMStrategy. Shared storage does not serialize concurrent read-modify-write transitions by itself.

Application pattern requiring the redis extra and application Redis configuration:

```python
from aiogram import Dispatcher
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

storage = RedisStorage.from_url(
    redis_url, key_builder=DefaultKeyBuilder(with_bot_id=True)
)
dp = Dispatcher(storage=storage, events_isolation=storage.create_isolation())
```

Choose TTLs, namespace, bot/account/topic identity and lock timeout for the application. `SimpleEventIsolation` supplies process-local keyed locking; Redis isolation coordinates workers using matching keys. Long external calls need deliberate lock duration/transaction boundaries. Restart survival is not a database backup or exactly-once delivery guarantee. Store orders/payment fulfillment/reminder intent in durable repositories with idempotency. Scenes Wizard can organize more complex reusable flows; use plain FSM when it is sufficient. Preserve or migrate serialized state names between releases. [FSM](https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/index.html), [storage](https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/storages.html), [Redis isolation implementation](https://docs.aiogram.dev/en/v3.31.0/_modules/aiogram/fsm/storage/redis.html), [Scenes](https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/scene.html).

At this pin, DefaultKeyBuilder's `with_bot_id` defaults to False. Two bots using the same Redis prefix/chat/user can therefore collide unless configured otherwise. The starter now includes bot_id and obtains isolation from that storage. Existing deployments changing their keys must migrate/expire the old namespace deliberately and give users a restart route; silently changing keys does not migrate active forms. Topic/business/destiny identity must also match the application's FSMStrategy and intended flow. [Key builder implementation](https://docs.aiogram.dev/en/v3.31.0/_modules/aiogram/fsm/storage/base.html).

## DI and middleware boundaries

Context values are injected by **parameter name**; type annotations aid clarity but do not select an arbitrary dependency by type. Standard names include `bot`, `state`, `event_from_user`, `event_chat` and matching filter outputs such as `command`/`callback_data`. Supply application services via Dispatcher contextual data, polling kwargs or middleware dictionaries; avoid overwriting framework keys.

Outer middleware runs before filters; inner middleware runs after filters and before the chosen handler. Scope middleware to the needed event type. A DB session example is a pattern: a BaseMiddleware async `__call__(handler, event, data)` enters an async session context, sets `data['session']`, awaits handler, and ensures rollback/close on failure. Decide whether filters also need the session before choosing outer versus inner registration. Never share one AsyncSession concurrently across updates.

Throttling requires application-specific limits/feedback. A process-local dictionary needs eviction and does not coordinate replicas. Silent drops can leave callback spinners or users stranded; answer rejected callbacks and return suitable feedback. Auth middleware may short-circuit without calling handler but must apply to all protected entry points. [DI](https://docs.aiogram.dev/en/v3.31.0/dispatcher/dependency_injection.html), [middleware](https://docs.aiogram.dev/en/v3.31.0/dispatcher/middlewares.html).

## Messages, files and formatting

`message.answer` sends to the same chat; `reply` creates a reply. Use Bot methods for explicit targets. Edit through Message/Bot; copy/forward/delete/pin are subject to Telegram rights and method restrictions. Reuse a bot's `file_id` rather than `file_unique_id` for re-sending. Defaults HTML needs `aiogram.html.quote` for user text; plain echoes should override `parse_mode=None`.

File types are distinct: `FSInputFile(path)` for disk, `BufferedInputFile(bytes, filename=...)` for bytes, `URLInputFile` for client-side fetching, or a plain URL when Telegram should fetch it. MediaGroupBuilder assembles an album; use keyword `media=` with its `add_photo`/other methods. Download via `bot.download(attachment, destination=...)` or `get_file` then `download_file`; validate destination names and actual size/format. Large media still obeys cloud/method limits; local Bot API server behavior differs. [File upload](https://docs.aiogram.dev/en/v3.31.0/api/upload_file.html), [media group builder](https://docs.aiogram.dev/en/v3.31.0/utils/media_group.html), [download](https://docs.aiogram.dev/en/v3.31.0/api/download_file.html).

## Webhooks, polling and shutdown

One polling process per bot token; remove an existing webhook deliberately before polling. Preserve pending updates unless discarding them is requested. `start_polling` handles poll backoff but does not automatically retry every failed Bot call. `tasks_concurrency_limit` bounds concurrent updates when `handle_as_tasks=True`; disabling tasks processes sequentially. Concurrency still needs state isolation and bounded application workers.

aiohttp webhook pattern requires a separately configured public HTTPS URL/secret and Router registrations:

```python
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

async def on_startup(bot):
    await bot.set_webhook(public_https_url + '/telegram', secret_token=webhook_secret,
                          allowed_updates=dp.resolve_used_update_types())

def run_receiver():
    dp.startup.register(on_startup)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=webhook_secret).register(
        app, path='/telegram'
    )
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='127.0.0.1', port=8080)
```

Create Bot/Dispatcher before this function; serve through configured TLS/proxy. `web.run_app` is a synchronous runner: do not put it inside an already running asyncio function. Public cloud webhook ports are Telegram-constrained; an internal proxy port may differ. Use a route secret distinct from the token; embedding the bot token in a path can leak through access logs. Configure allowed updates, request sizes, health and retries.

For FastAPI/another ASGI framework, implement lifespan startup/shutdown, validate the secret header, construct `Update.model_validate(payload, context={'bot': bot})`, then `await dp.feed_update(bot, update)` or the documented webhook variant. Decide whether to await work or acknowledge after **durably** enqueuing it. Background acknowledgment can lose updates on process death; Telegram retries can duplicate already performed effects. Inspect returned TelegramMethod if implementing webhook-response optimization; it cannot report normal API-call results.

Stop receiving, await/cancel owned work, emit framework shutdown and close bot sessions/FSM/DB/HTTP resources. Handle partial startup failure. Do not automatically delete a shared webhook when a rolling-deployment replica exits. [Dispatcher](https://docs.aiogram.dev/en/v3.31.0/dispatcher/dispatcher.html), [webhook integration](https://docs.aiogram.dev/en/v3.31.0/dispatcher/webhook.html).

`tasks_concurrency_limit` bounds spawned polling update tasks when `handle_as_tasks=True`; it does not make state durable or guarantee those tasks drain before resources close. At 3.31.0, start_polling's shutdown stops polling tasks and emits shutdown without awaiting its tracked per-update task set. If completing work before shutdown is required, use application-supervised workers/inbox records, or choose sequential `handle_as_tasks=False` when suitable, and define recovery for interrupted work. Do not rely on the dispatcher's private task set as a stable integration API. [Pinned dispatcher implementation](https://docs.aiogram.dev/en/v3.31.0/_modules/aiogram/dispatcher/dispatcher.html).

## Scheduling and restart recovery

aiogram has no bundled JobQueue. For APScheduler **3.x**, use `AsyncIOScheduler` with an explicit timezone; pin `APScheduler>=3.10,<4` if adopting this API. Register cron/interval/date jobs inside the application's running loop and shut down the scheduler during owned shutdown. The application supplies async callbacks, Bot/service arguments, job IDs and misfire/coalescing policy. Do not paste a v4 scheduler API into a v3 recipe.

Persistent reminder records and claiming/recovery logic are separate from FSM Redis storage. Multiple webhook workers must not all start the same periodic delivery job. Prefer one scheduler owner or a coordinated durable worker. Retry/duplicate delivery policy belongs to the task record. [APScheduler 3 user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html).

## Translation

Install the i18n extra. Configure `I18n(path='locales', default_locale='en')` and `SimpleI18nMiddleware(i18n).setup(router)`. Extract/translate `.po` catalogs and compile `.mo` files; add locale fallback and persist explicit user choices if needed. Use gettext within the active locale; lazy gettext is useful in filters but must not be passed into Telegram model fields expecting real strings. Escape interpolated user content after translation. More complex localization can use a documented alternative rather than a homegrown global locale. [Translation](https://docs.aiogram.dev/en/v3.31.0/utils/i18n.html).

## Errors, project layout and verification

Register router/dispatcher ErrorEvent handlers; `True` handles the error, it does not replay the failed method. Distinguish TelegramForbiddenError (access removed), TelegramBadRequest (fix request), TelegramRetryAfter (wait specified seconds), and TelegramNetworkError (possibly unknown outcome). Bounded request-level retry can rerun explicit rate-limit failures; timeouts on sends/payments can require reconciliation rather than blind replay. Avoid logging tokens/full updates; optional admin reports need independent failure handling and rate limits. [Errors](https://docs.aiogram.dev/en/v3.31.0/dispatcher/errors.html).

Keep config/lifecycle, routers, keyboards/CallbackData, middleware, states, repositories and business services separate when useful. Use reusable async HTTP clients and per-request DB sessions; offload blocking work while keeping framework objects on their event loop. Protect external writes through transactional/idempotent business services.

Run `python assets/starter/offline_check.py` with requirements installed. Also exercise routing of actual fabricated Updates through `Dispatcher.feed_update` with a mocked Bot session when extending the app. Validate concurrent forms, cancellation/reentry, nontext input, callback limits/expiry, Redis key migration, failed operations and shutdown. Dedicated live tests confirm TLS, webhook secret rejection, permission grants, inline/BotFather settings, command scopes and actual delivery. Report offline and live outcomes separately.

## State and routing recovery

| Symptom | Inspect first | Expected behavior |
| --- | --- | --- |
| A command is consumed as form input | Command/state-wide handler order and F filters | Cancellation/reentry commands win; the form remains in its step after invalid content |
| Old buttons spin or reach the wrong handler | CallbackData prefix/version and fallback position | A final callback route acknowledges unknown payloads with a recovery action, without interpreting them as new commands |
| One bot sees another bot's form | Redis key builder, bot_id, matching isolation | State and locks have account/flow-scoped keys |
| A completion reply fails | clear/update ordering and durable operation status | Keep demo data until the reply succeeds; reconcile an already committed business effect before retrying it |
| Dependency injection fails | Context dictionary keys and filter outputs | Parameter names match injected services; no accidental override of framework keys |

Use state-specific hints for unexpected media, keep a cancellation route visible, and preserve accepted answers when validation fails. Localize prompts/buttons in the same request locale, and translate before escaping interpolated user content. Provide a clear final summary; a keyboard disappearing alone is insufficient completion feedback. When throttling a callback, acknowledge it and explain the retry route. Read [bot UX](../../telegram-bot-ux/SKILL.md) for navigation/copy, [accessibility](../../telegram-bot-accessibility/SKILL.md) for nonvisual and localized checks, and [Mini App design](../../telegram-bot-miniapp-design/SKILL.md) with [Mini App security](../../telegram-bot-miniapps/SKILL.md) for a requested web surface.
