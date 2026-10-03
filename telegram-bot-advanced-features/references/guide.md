# Durable bot engineering guide

Checked 2026-10-03. Contents: state/session lifecycle; scheduling; inbox/outbox/retries; webhooks/deployment; broadcasts; local API; logs/tests/troubleshooting. [Sources](sources.md) give verified scopes. These are design patterns and tested local utilities, not a deployable full bot.

## Persistent state and database lifecycle

Keep temporary conversation state in the framework's FSM/user data when appropriate; choose persistence for restart requirements. Business balances, entitlements, orders, profiles and schedules belong in transactional records with unique constraints. Key ownership by Telegram numeric IDs. An in-memory cache is acceptable for derived data, not as the only durable source of paid access.

The corrected async structure is:

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

engine = create_async_engine(database_url)
sessions = async_sessionmaker(engine, expire_on_commit=False)

# One session per operation/task:
async with sessions() as session:
    async with session.begin():
        # Query/write application records here; rollback occurs on exceptions.
        ...
# During application shutdown:
await engine.dispose()
```

This is a lifecycle fragment, not an initialization script. Use Alembic/your chosen migration tool for production schema changes, a suitable async driver and pool/timeouts for the database, explicit eager loading to avoid implicit async I/O, and a dialect-specific upsert or uniqueness/retry strategy for concurrent create-or-get.

[The runnable SQLite example](../scripts/state_lifecycle.py) imports `Mapped`, defines a separate base, uses a real timestamp column and SQLite `on_conflict_do_nothing`, and disposes the engine. Run `python telegram-bot-advanced-features/scripts/state_lifecycle.py` after installing SQLAlchemy 2/aiosqlite; it creates a temporary local database and performs no Telegram calls. Port the upsert using the chosen backend's documented dialect, not a `postgres+asyncpg` typo; the PostgreSQL async URL is `postgresql+asyncpg://...`.

For aiogram multi-worker conversations, choose [RedisStorage](https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/storages.html) and matching key strategy/TTL. Redis centralizes state but does not serialize simultaneous updates by itself; add event isolation/locking or route a conversation consistently when transitions must be sequential. Define cleanup and close the storage at shutdown. PTB persistence and conversation concurrency settings likewise need an intentional policy; they do not replace a payment ledger.

## Scheduling and background jobs

PTB JobQueue requires the `job-queue` optional dependency. Its coroutine callback receives context; `run_daily` takes a timezone-aware `datetime.time`, with `tzinfo=`, not `tz=`. PTB weekdays map Sunday=0, unlike APScheduler cron weekdays.

```python
from datetime import time
from zoneinfo import ZoneInfo

async def digest(context):
    # Read due work / publish an outbox intent using application services.
    await digest_service.enqueue_due()

app.job_queue.run_daily(digest, time(hour=9, tzinfo=ZoneInfo("Asia/Kolkata")))
```

`digest_service` is your implementation. In aiogram with **APScheduler 3.x**, `AsyncIOScheduler` runs coroutine jobs on the active event loop; bind startup/shutdown to the application. Do not transpose APIs from APScheduler 4. Choose coalescing, `misfire_grace_time`, `max_instances`, time zone and daylight-saving behavior explicitly.

For durable per-user reminders, persist due time/status/recipient/payload and an idempotency key in a job table. A poller claims due rows transactionally, enqueues delivery, and acknowledges only according to the declared delivery policy. Store UTC instants plus original timezone rules for recurring local-time schedules. A process-local timer need not survive restart; use a persistent scheduler/job store or DB-driven due-work service when it must.

APScheduler 3 job stores should not be shared across independent schedulers as a coordination scheme. Elect one scheduler or use a queue-backed worker architecture. Do not claim that restarting an in-memory JobQueue preserves future tasks automatically.

## Inbox, outbox and retry policy

Webhook retries, repeated polling offsets and concurrent workers can produce duplicate work. Store an inbound `update_id` with a unique constraint scoped to the bot. Commit the update/work intent before acknowledging durable receipt. Duplicate receipt is a successful no-op once the durable record exists; processing failures remain visible for retry/manual resolution.

For a business mutation plus external notification, insert the notification outbox row in the **same transaction** as the business change. This requires integrating the outbox table/service with the business database; the standalone SQLite helper's separate `enqueue()` call does not magically join another service's transaction.

The local [Outbox helper](../scripts/durable_ops.py) provides dedupe keys, persisted attempt counts, due times, unique lease tokens and states: pending, inflight, sent, blocked, failed and uncertain. Claim/ack fencing prevents an expired worker from overwriting a newer lease. A crashed non-replay-safe job becomes uncertain; a replay-safe job can be reclaimed. Separate sessions/connections are used per call. Call these synchronous SQLite operations through `asyncio.to_thread` when integrating them into an async event loop.

`safe_replay=True` means **your receiver/action** tolerates repeated execution. A normal Telegram `sendMessage` has no client idempotency key and is generally not replay-safe. Choosing at-least-once notifications and accepting occasional duplicates is a product decision; reconciliation/manual review may be better for high-impact sends, refunds or spending. A lease does not prevent a slow worker's external side effect after expiry; use appropriate deadlines and never claim exactly-once external delivery.

Classify errors by context:

| Outcome | Policy |
|---|---|
| Confirmed rate-limit rejection | Persist a retry no earlier than `retry_after`; support integer or timedelta wrapper representations |
| Timeout/network/5xx with uncertain mutation | Mark uncertain/reconcile unless an explicit replay policy allows another attempt |
| Bad request, revoked token, unsupported parameter | Fail and fix configuration/input; no blind backoff loop |
| Forbidden private recipient | Stop that recipient when the response confirms blocked/unreachable |
| Missing channel rights or wrong chat | Repair configuration; do not label every Forbidden as user blocked |
| Safe/idempotent transient operation | Bounded exponential delay plus optional jitter/deadline |

The deterministic retry helper caps attempts and preserves long Telegram retry delays rather than shortening them. Production workers may add bounded jitter, centralized per-chat/global budgets and a total deadline. Never swallow cancellation; release/mark leases according to the known outcome and shutdown policy. Idempotent edit-to-a-known-state operations can be replayed with appropriate handling of “message not modified”; create/send/spend operations need their own uncertainty policy.

PTB `AIORateLimiter` requires the `rate-limiter` optional dependency and defaults to `max_retries=0`. It is a reference limiter, not a universal network-error retry mechanism. If multiple sender processes share a token, coordinate budgets centrally rather than assuming each process may use the full quota.

## Webhooks and deployment

Polling and webhooks are mutually exclusive; remove the webhook before switching to polling. Multiple bots may run in one process, but do not run competing long-poll consumers for one token. Horizontal webhook workers require shared inbox/state/queue coordination.

Register an HTTPS endpoint with a strong independent webhook secret, appropriate `allowed_updates`, `max_connections`, and a deliberate pending-update policy. Hosted webhook ports are 443/80/88/8443; this does not make plaintext HTTP valid for the hosted API. Secrets allow 1–256 ASCII letters/digits/underscore/hyphen. The receiver must verify the header before JSON/handler work. Use [valid_webhook_secret](../scripts/durable_ops.py) or the framework's documented secret validation.

For aiogram's aiohttp `SimpleRequestHandler`, supply `secret_token`. Its background handling option acknowledges before the handler finishes, so it does not by itself provide a durable inbox. Decide whether the endpoint waits for completion or first commits into a durable queue; ensure failure behavior preserves accepted work. PTB's webhook runner has its own verification/runtime optional dependency; check the installed version.

Terminate TLS at the service or reverse proxy. Preserve the secret header, restrict backend listener exposure, enforce actual body limits/read timeouts, and trust forwarded headers only from your proxy. Respond success only after the receiver's durability criterion; return non-success on failure to persist. Keep registration separate from an example receiver so simply starting a local utility cannot mutate a live webhook.

An nginx location integration fragment (inside an already configured TLS server):

```nginx
location = /telegram-hook {
    client_max_body_size 1m;
    proxy_read_timeout 15s;
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Telegram-Bot-Api-Secret-Token $http_x_telegram_bot_api_secret_token;
}
```

Choose the body size/timeout for your update mix. A valid certificate and HTTP listener/application route are separate setup requirements; this fragment does not provision either.

A container fragment for your existing `main.py` project:

```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home --uid 10001 bot
COPY --chown=bot:bot . ./
USER bot
CMD ["python", "main.py"]
```

The tag is an illustrative base selection; resolve and pin its current digest before a reproducible release, rather than copying a fictional digest. Lock dependency versions, exclude `.env`, tokens, session files, databases and `.git` from the build context, inject secrets at runtime, and mount persistent storage with correct ownership. Docker image creation does not configure database backups, TLS, health routing or orchestration.

Use `TELEGRAM_BOT_TOKEN`, `WEBHOOK_SECRET`, `WEBHOOK_URL` and `DATABASE_URL` as clear example project environment names; they are local conventions, not Telegram-required names. A systemd deployment may load a protected environment file and run a dedicated user/virtualenv. Do not embed the token in a unit committed to the repository.

Shutdown should stop acceptance/claims, finish or classify in-flight work within a deadline, close bot HTTP sessions/storage and dispose the DB engine. Expose liveness separately from readiness (database/queue dependencies). Back up persistent state and rehearse restore; a backup that has never been restored is unverified.

## Broadcasts and rate budgets

Page recipients from persistent storage using a stable cursor; do not load a million-user list or create unlimited tasks. Record campaign/recipient status and cancellation checkpoint. Require appropriate recipient eligibility and stop known blocked users. A user's unblocking update may restore eligibility according to product policy; do not claim repeated Forbidden responses automatically ban the bot.

The [FAQ](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this) gives approximate free broadcast and per-chat/group guidance. Use separate per-chat/group and global budgets; current traffic from normal replies counts too. Start conservatively and honor actual rate-limit feedback rather than elevating 20–25 messages/s into a guarantee.

Paid broadcasts can raise throughput and spend Stars through `allow_paid_broadcast`; enable only for an explicit budgeted use case after checking current eligibility/rates. Keep it off in ordinary snippets/tests. Monitor fees as part of reconciliation. Serialize per-chat ordering where the campaign depends on it; bounded concurrency across independent recipients can improve efficiency.

## Local Bot API server

The official [telegram-bot-api](https://github.com/tdlib/telegram-bot-api) server can be deployed near your bot for documented file/network capabilities. Download limits become unrestricted by file size; uploads support up to **2000 MB**. Local webhook addresses/ports and absolute file paths have distinct behaviors. Rate/content/permission constraints are not all removed.

The server itself requires an API ID/hash (`TELEGRAM_API_ID` / `TELEGRAM_API_HASH` or documented command-line options); the bot still authenticates with its bot token. Enable `--local` for the expanded local capabilities. Use the framework's documented base API and file URL configuration; match shared file-path accessibility to deployment topology. Follow Telegram's `logOut` migration procedure before switching from hosted operation; do not run mismatched hosted/local consumers concurrently. Do not expose the local API service to the public internet without appropriate access controls. MTProto libraries are a separate transport with separate credentials/session limits, not a blanket Bot API file-limit bypass.

## Logging, tests and troubleshooting

Emit structured records containing bot/update/job/campaign IDs, method, outcome, duration and retry count. Redact bot tokens in request URLs, webhook secrets, Mini App initData, session tokens and sensitive payment/profile content. Ordinary text rotating logs are not a turnkey JSON/Sentry integration. Choose the logger/exporter for the actual deployment; avoid blocking file/network log handlers in an async loop.

Track oldest queue age, retries/uncertain work, successful sends, webhook failure/backlog, DB errors and payment reconciliation. Admin notifications need their own rate limiting/redaction so a failure cannot cause a notification loop.

Run:

```text
python -m unittest discover -s telegram-bot-advanced-features/scripts -p 'test_*.py' -v
```

Tests include concurrent claim/upsert, lease fencing, crash uncertainty, restart persistence, bounded delays, duplicate/conflicting intents and secret mismatch. Use mocked framework handlers and in-process HTTP endpoints for additional tests. A separately authorized staging bot can verify actual Telegram integration; avoid accidental live recipients/payments.

| Symptom | Investigate |
|---|---|
| Spinner after a tap | Callback not answered; long work before acknowledgment |
| No updates | Webhook/polling conflict, wrong allowed updates, receiver rejection |
| 409 polling conflict | Competing consumer for the same token |
| Entity parsing error | Parse-mode escaping and UTF-16 entities |
| 429 | Respect retry metadata and coordinate budgets |
| Forbidden | Recipient block versus chat rights/context; distinguish them |
| Duplicate fulfillment | Missing unique receipt/transaction boundary or concurrent processing |
| Reminder lost on restart | Ephemeral timer or work acknowledged before persistence |
| Healthy process, no progress | Queue age/readiness/DB errors, not only process liveness |
