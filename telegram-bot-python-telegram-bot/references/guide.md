# PTB implementation guide

Research cutoff: **2026-10-03**. Target **22.8** unless the project pins another version. [Source register](sources.md) records verified scope. This guide contains **application patterns**; only `assets/starter/bot.py` is supplied as a complete polling entrypoint.

Contents: setup and migration; handlers/context; callback menus; conversations/persistence; scheduling; media; lifecycle/webhooks; inline/admin features; errors/performance; verification; recovery and interface diagnostics.

## Setup and compatibility

For a new project, install `python-telegram-bot==22.8`; add extras only for used features: `job-queue`, `rate-limiter`, `webhooks`, `callback-data`, `socks`, `http2`, or `passport`. Multiple extras share one requirement, e.g. `python-telegram-bot[job-queue,rate-limiter,webhooks]==22.8`. The starter needs the first two. Its environment names are local conventions: `BOT_TOKEN` and optional `BOT_STATE_FILE`. Keep state files writable and trusted, separate from application code.

PTB 22.8 documents native API 10.0 support; Telegram's 2026-08-24 update is API 10.3. A newer field may require upgrading or the official PTB forward-compatibility approach; `api_kwargs` passes extra arguments on supported methods but does not create a missing method or return type. Review signatures and response handling first. Async v20+ examples cannot be pasted into old synchronous Updater/Dispatcher applications. [Installation/support](https://docs.python-telegram-bot.org/en/v22.8/), [changelog](https://docs.python-telegram-bot.org/en/v22.8/changelog.html), [forward compatibility](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Bot-API-Forward-Compatibility).

## Handlers, filters and context

Each Application group runs at most its first matching handler; groups are considered in numeric order. Put commands, conversations and specific callbacks before generic MessageHandlers in the same group. Raise `ApplicationHandlerStop` to prevent later groups. Use `TypeHandler(Update, ...)` only for intentional broad routing.

| Update/task | Handler/filter |
| --- | --- |
| Commands/text | `CommandHandler`; `MessageHandler(filters.TEXT & ~filters.COMMAND, ...)` |
| Photos/documents/voice | `filters.PHOTO`, `filters.Document.ALL`, `filters.Document.MimeType(...)`, `filters.VOICE` |
| Private/groups/user/chat | `filters.ChatType.PRIVATE`, `filters.ChatType.GROUPS`, `filters.User(...)`, `filters.Chat(...)` |
| Callback/inline | `CallbackQueryHandler`, `InlineQueryHandler`, `ChosenInlineResultHandler` |
| Membership/join requests | `ChatMemberHandler`, `ChatJoinRequestHandler` |
| Payments/poll responses | `ShippingQueryHandler`, `PreCheckoutQueryHandler`, `PollAnswerHandler` |
| Reactions/business updates | Dedicated handlers in the installed reference, with explicit update subscriptions |

Combine filters with `&`, `|`, `~`; parenthesize comparisons. Use `filters.StatusUpdate` for service messages. There is no `StatusFilter.ADMIN`; check current admin rights through the API. Custom message predicates use `MessageFilter`; whole-update predicates use `UpdateFilter`.

Context carries `bot`, `application`, command `args`, user/chat/bot data, optional `job_queue`, job `job` and error-handler `error`. Namespace data so flows coexist. A job has no incoming message. `update.effective_message`, user and chat may be absent; callback/inline/membership updates cannot be handled by assuming `update.message.text`. [Routing](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.application.html#telegram.ext.Application.add_handler), [filters](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.filters.html), [context](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.callbackcontext.html).

## Callback menus and pagination

`CallbackQueryHandler(pattern=...)` supports regex, callable or type, not `filters.CallbackQuery`. Regex uses `re.match`; anchor complete payloads when needed. Unexpected client data is possible: even `page:12` needs bounds checks and server-side lookup. String callback data is 1–64 **UTF-8 bytes**. Arbitrary-object callback data needs the extra and can yield `InvalidCallbackData` after cache expiry/restart.

Answer promptly, authorize the actor, load data and edit. `query.edit_message_text` / `edit_message_reply_markup` support normal/inline callbacks. For message-dependent operations, check for an accessible `telegram.Message`; otherwise use an inline ID or handle an expired menu. Keep prices/permissions on the server. Shared group menus may need an owner check. Catch the specific unchanged-message BadRequest only when benign; preserve unrelated failures. [Handler](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.callbackqueryhandler.html), [CallbackQuery](https://docs.python-telegram-bot.org/en/v22.8/telegram.callbackquery.html).

## Conversations and persistence

Use entry points, state handlers and `/cancel` fallbacks; return the next state or `ConversationHandler.END`. Place these before generic text handlers. A button-driven state needs a **separate callback handler** reading `update.callback_query.data`; a text callback reading `update.message` is not reusable for buttons.

Defaults key conversations by chat and user. Deliberately choose `per_chat`, `per_user`, `per_message`: message-based identity is for callback-driven flows, not arbitrary text steps. `allow_reentry=True` restarts through entry points. Timeouts need JobQueue; nested timeout combinations have documented limitations. Register persisted conversations before initialization and retain stable names/state IDs across releases.

The starter uses `concurrent_updates(False)`, private form entry points and namespaced user data. If a user runs independent forms in multiple chats, store form data by the same `(chat_id, user_id)` key rather than one user-wide form dictionary. Clear only this flow's data.

Restart survival needs Application persistence **and** conversation `name` **and** `persistent=True`. PicklePersistence writes selected data/opted-in conversations on its interval (default 60 seconds) and lifecycle flush, not a transaction per update. Only load trusted pickle files. Business orders/payments/reminders need transactional database records. Custom BasePersistence can implement another backend; a local pickle file is not shared multi-worker storage. Values must be safely copyable because PTB copies data before persistence. [ConversationHandler](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.conversationhandler.html), [PicklePersistence](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.picklepersistence.html), [BasePersistence](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.basepersistence.html).

## JobQueue: units, timezone and recovery

JobQueue uses APScheduler 3's AsyncIOScheduler and needs the extra. Numeric `when`, `interval` and `first` are seconds. `/remind 30` means `when=30 * 60`; `timedelta(minutes=30)` avoids ambiguity. Validate finite positive delays and application-specific bounds.

Application pattern with a built app and application-owned async callbacks/record IDs:

```python
from datetime import time, timedelta
from zoneinfo import ZoneInfo

jq = app.job_queue
jq.run_once(send_reminder, when=timedelta(minutes=30), chat_id=chat_id, data=record_id)
jq.run_repeating(check_due_records, interval=60, first=5)
jq.run_daily(daily_digest, time=time(9, 0, tzinfo=ZoneInfo('Asia/Kolkata')))
jq.run_monthly(monthly_digest, when=time(9, 0, tzinfo=ZoneInfo('UTC')), day=1)
```

Use `context.job.data`, `.chat_id` and `context.bot`. Scheduling with `chat_id`/`user_id` enables related context data. Use stable names, `get_jobs_by_name` and `schedule_removal` for cancellation. For an immediately run repeating job call `await job.run(app)`; `first=0` is not enough. Naive schedule times use Defaults' timezone, UTC by default. Test daylight-saving behavior.

PTB persistence does **not** automatically save JobQueue jobs. Store due time/intent/status durably, restore/reconcile on startup and claim records transactionally across workers. Delivery after failure can be at least once; design recovery and duplicate handling. [JobQueue](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.jobqueue.html).

## Messages, media and formatting

Async operations include send/edit/delete/pin/copy/forward and Message shortcuts. Reuse `file_id` when appropriate; `file_unique_id` cannot send/download. Download via `get_file()` and `download_to_drive`/`download_to_memory`, validating the destination path.

Local uploads accept supported path/file/bytes inputs; keep file handles open across the awaited upload. `InputFile(..., read_file_handle=False)` avoids eager reads but still depends on backend file I/O. An `aiofiles` wrapper is **not** a drop-in synchronous PTB file object. Obtain modest generated bytes asynchronously; for huge files avoid loading everything into memory and verify backend behavior. Albums use appropriate InputMedia classes and Telegram's grouping limits.

With HTML Defaults, escape user content using `html.escape`; plain echoes can set `parse_mode=None`. MarkdownV2 uses `escape_markdown(..., version=2)`. Split long outputs without breaking markup/entities. Cloud `getFile` downloads currently cap at 20 MB; upload, URL-fetch and local-server limits differ. [InputFile](https://docs.python-telegram-bot.org/en/v22.8/telegram.inputfile.html), [File](https://docs.python-telegram-bot.org/en/v22.8/telegram.file.html), [helpers](https://docs.python-telegram-bot.org/en/v22.8/telegram.helpers.html), [Telegram file limits](https://core.telegram.org/bots/api#getfile).

## Polling, webhooks and embedded lifecycle

Ordinary scripts call synchronous `run_polling`/`run_webhook`, which manage their event-loop lifecycle; they do not simply call `asyncio.run`. Never nest these runners in an already running loop. Manually managed applications must invoke needed post-init/stop/shutdown hooks themselves.

Behind a configured TLS reverse proxy, application pattern requiring the `webhooks` extra:

```python
app.run_webhook(
    listen='127.0.0.1', port=8080, url_path='telegram',
    webhook_url=public_https_url + '/telegram', secret_token=webhook_secret,
    allowed_updates=['message', 'callback_query'], drop_pending_updates=False,
)
```

Keep the default Updater for PTB's receiver. `.updater(None)` is for a **custom** service validating the Telegram secret header, parsing `Update.de_json(payload, app.bot)` and enqueuing into `app.update_queue`. There is no updater to call. Register the public webhook when the receiver is ready; choose bounded queue/acknowledgment semantics appropriate to durable processing. TLS, request-size limits and proxy ownership remain application concerns.

For manual polling integration: initialize the Application; call required post-init logic; start its existing Updater polling; start the Application; await the host shutdown event; stop the Updater; stop/shut down the Application in `finally`. Track which startup stages succeeded. For a custom webhook, initialize/start the Application and receiving service, then stop receiving before stopping/shutting down the Application. Await/cancel owned tasks and close DB/HTTP resources. Application `start()` alone does not fetch updates.

One polling worker per token; webhook replicas need shared state/idempotency. A webhook is not automatically faster or suitable for every serverless environment. Switching modes does not imply permission to drop pending updates. [Application](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.application.html), [Updater](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.updater.html), [custom receiver example](https://docs.python-telegram-bot.org/en/v22.8/examples.customwebhookbot.html), [Telegram webhook](https://core.telegram.org/bots/api#setwebhook).

## Inline, deep links, groups and other update families

Enable inline mode in BotFather. Answer promptly with stable result IDs, bounded results, `next_offset` and deliberate `cache_time`/`is_personal`. Current PTB uses `button=InlineQueryResultsButton(...)`, not removed `switch_pm_text`. Handler registration does not grant Telegram features or permissions.

Use `create_deep_linked_url`; validate command payloads as untrusted identifiers. Register commands/scopes through `set_my_commands`; visibility is not authorization. Moderation checks both the actor and bot's relevant rights. Anonymous sender-chat messages need an explicit policy; restrictions apply to supergroups. Use aware temporary restriction times. Carry thread/business IDs for the relevant workflows, and update stored chat IDs on migration. Explicitly subscribe to membership/reaction/business/payment updates as needed; include `chat_member` when that handler needs it. [InlineQuery](https://docs.python-telegram-bot.org/en/v22.8/telegram.inlinequery.html), [Bot methods](https://docs.python-telegram-bot.org/en/v22.8/telegram.bot.html), [deep links](https://core.telegram.org/bots/features#deep-linking).

## Errors and asynchronous performance

Register an error handler. Log useful identifiers without token URLs, sensitive bodies or full Updates. Optional admin reports need configured numeric IDs, escaping, rate limits and independent failure handling. Distinguish Forbidden (lost access), BadRequest (fix inputs/permissions), RetryAfter (wait), and TimedOut/NetworkError (possibly unknown outcome). Sleeping in an error callback does not rerun the failed operation.

AIORateLimiter's default `max_retries` is zero; choose a bounded retry count. It is not exact per-chat accounting or a broadcast guarantee. Coordinate quotas across replicas; persist broadcast cursors/inactive users and use bounded batches. Invalid requests should not enter retry loops. Reconcile business side effects before retrying ambiguous responses.

Reuse async HTTP clients/DB sessions. Move unavoidable blocking calls to `asyncio.to_thread`, keeping PTB objects on their event loop; use workers for CPU-heavy work where needed. Stateless concurrency can use `concurrent_updates(n)` after reviewing ordering/shared state and tuning pool capacity/timeouts. HTML Defaults is a formatting choice, not a speed optimization. [Errors](https://docs.python-telegram-bot.org/en/v22.8/telegram.error.html), [limiter](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.aioratelimiter.html), [builder](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.applicationbuilder.html).

## Project layout and checks

Separate config, handler registration, keyboards, services, repositories and lifecycle as complexity warrants. Modules can expose `register(app)` before initialization. Keep per-request DB resources out of persisted context; persist versioned records rather than clients/application objects.

Run `python assets/starter/offline_check.py` with starter requirements installed. A copied application should also exercise routing overlap, nontext messages, expired callbacks, permission denial, cancellation/reentry, invalid input, restart state, scheduling units, duplicate delivery and graceful stop. Dedicated live checks confirm privacy/inline settings, actual admin rights, TLS/secret validation and update subscriptions. Report offline and live validation separately.

## Recovery and interface diagnostics

ConversationHandler applies a returned state after the awaited callback finishes. In the demo, change form data only after the transition's reply succeeds: reset it after a reentry prompt, record the name after the age prompt, and remove it after completion/cancellation confirmation. If a reply raises, the old state and input remain usable. This prevents a local retry from crashing; it does not make an ambiguous Telegram send or a database write exactly once. Real forms should commit their business record with an operation ID, then recover/render its actual status rather than repeating fulfillment when the user retries.

| Symptom | Inspect | Useful next check |
| --- | --- | --- |
| A photo during a text step gets silence | State-specific filters and fallback order | Route nontext input to a hint that returns None, preserving the current state |
| A button spins after a deployment | Callback schema, expired arbitrary-data cache, subscription | Place a recovery CallbackQueryHandler last in the group; acknowledge and offer `/menu` without executing unknown data |
| Conversation resets after restart | Persistence wiring, stable name/state keys, file access | Restore an actual opted-in conversation; pickle presence alone is insufficient |
| Conversation mixes users or messages | per_chat/per_user/per_message and concurrent_updates | Verify the intended conversation key and sequential processing before changing the handlers |
| Handler is never reached | First match in each group and allowed_updates | Use an actual Update fixture, including command entities and optional fields |

Prompts should state the accepted input and a cancellation route; repeat the current step after validation failure without removing already accepted data. Keep completion copy truthful about the demo or persisted result. Acknowledging a button removes the loading indicator; the edited message must separately describe what happened. Use readable action labels and a text/command alternative where the task needs it. Review [bot UX](../../telegram-bot-ux/SKILL.md) for flow design and [accessibility](../../telegram-bot-accessibility/SKILL.md) for assistive-technology, language and text-alternative checks. For a requested web interface, add [Mini App design](../../telegram-bot-miniapp-design/SKILL.md) and [Mini App security](../../telegram-bot-miniapps/SKILL.md); a ConversationHandler does not validate web launch data.
