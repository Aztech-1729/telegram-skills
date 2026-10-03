---
name: |
  telegram-bot-advanced-features
description: |
  Load this skill for production Telegram bot engineering: state management beyond basics (DB-backed state, multi-user broadcasts), background jobs/scheduling, persistent storage (SQLAlchemy async, Redis), webhook deployment (Docker, nginx, TLS, secret tokens), local Bot API server, broadcast to large audiences, rate-limit strategy, structured logging, testing, monitoring, and troubleshooting with complete examples.
---

# Telegram Bot Production Engineering

## 1. State management beyond the default

Framework FSM (PTB user_data / aiogram FSMContext) is for conversation flow only. Business state (balances, subscriptions, user profiles) belongs in a database:

```python
# SQLAlchemy 2.0 async pattern (works with PTB and aiogram)
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///bot.db")   # postgres+asyncpg:// in prod
Session = async_sessionmaker(engine, expire_on_commit=False)

class User(sa.orm.DeclarativeBase):
    __tablename__ = "users"
    id: Mapped[int] = sa.orm.mapped_column(primary_key=True)   # telegram user id
    joined: Mapped[str] = sa.orm.mapped_column(default=sa.func.now())
    balance: Mapped[int] = sa.orm.mapped_column(default=0)
    locale: Mapped[str] = sa.orm.mapped_column(default="en")

async def get_or_create_user(session, tg_id: int) -> User:
    user = await session.get(User, tg_id)
    if user is None:
        user = User(id=tg_id)
        session.add(user)
        await session.commit()
    return user
```

Rules: never store business state in Python globals (multi-user bots corrupt them); key everything by Telegram's numeric IDs, not usernames (usernames change); for aiogram FSM with multiple workers use Redis storage.

## 2. Jobs and scheduling

```python
# PTB JobQueue (APScheduler)
jq.run_repeating(sync_task, interval=300, first=10)
jq.run_daily(digest, time=time(hour=9, tz=ZoneInfo("Asia/Kolkata")))
jq.run_once(after_10, when=60, chat_id=cid, data={"x": 1})

# aiogram + APScheduler
scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
scheduler.add_job(digest, "cron", hour=9, minute=0, args=[bot])
scheduler.start()

# Scheduled messages per user — pattern
# 1. DB table: reminder(chat_id, at, text, sent)
# 2. Every minute a job queries due rows and sends, marking sent
```

For cross-restart durability, put future jobs in the DB with a poller job rather than in-memory queues (JobQueue/FSM state can be lost without persistence).

## 3. Webhooks — production deployment

### 3.1 When webhook vs polling

| | Polling | Webhook |
|---|---|---|
| Setup | zero | TLS + public endpoint |
| Latency | ~good | best |
| Serverless | no | yes |
| Multiple bots/processes | fine | fine (one per token) |
| Local dev | ✅ | needs tunnel |

### 3.2 Registering the webhook

```python
await bot.set_webhook(
    url="https://bot.example.com/hook/<random64hex>",
    secret_token=SECRET,                 # echoed in X-Telegram-Bot-Api-Secret-Token
    max_connections=100,
    drop_pending_updates=False,
    allowed_updates=["message", "callback_query", "pre_checkout_query"],
)
```

Verify every incoming request's `X-Telegram-Bot-Api-Secret-Token` and reject mismatches with 403. Ports allowed: 443, 80, 88, 8443.

### 3.3 Dockerfile (either framework)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

Systemd for bare metal:

```ini
[Unit]
Description=Telegram bot
After=network-online.target

[Service]
Environment=TELEGRAM_BOT_TOKEN=changeme
WorkingDirectory=/opt/bot
ExecStart=/opt/bot/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.4 Local Bot API server (big files, no limits)

For files >20/50 MB or high traffic, run the official `telegram-bot-api` binary locally and point the library at it:

```python
# PTB
app = Application.builder().token(TOKEN).base_url("http://localhost:8081/bot").base_file_url("http://localhost:8081/file/bot").build()
```

The local server raises upload/download limits (up to 2 GB) and serves files over your LAN.

## 4. Broadcast to large audiences — the hard part

```python
import asyncio
from telegram.error import Forbidden, RetryAfter

async def broadcast(bot, user_ids: list[int], text: str) -> dict:
    stats = {"ok": 0, "blocked": 0, "failed": 0}
    batch = 25
    for i in range(0, len(user_ids), batch):
        results = await asyncio.gather(
            *(send_one(bot, uid, text) for uid in user_ids[i:i+batch]),
            return_exceptions=True,
        )
        for uid, res in zip(user_ids[i:i+batch], results):
            if isinstance(res, Forbidden):
                stats["blocked"] += 1
                await mark_inactive(uid)          # remove from future broadcasts
            elif isinstance(res, RetryAfter):
                await asyncio.sleep(res.retry_after)
                await send_one(bot, uid, text)     # retry once
                stats["ok"] += 1
            elif isinstance(res, Exception):
                stats["failed"] += 1
            else:
                stats["ok"] += 1
        await asyncio.sleep(1)   # ~25 msgs/sec — stay well under limits
    return stats

async def send_one(bot, uid, text):
    return await bot.send_message(uid, text)
```

Rules: read IDs from DB in pages (never load 1M rows into RAM), track inactive/blocked users and stop messaging them (message them again and Telegram may ban the bot), prefer rate ~20-25 msg/s, honor RetryAfter, make broadcast resumable (checkpoint row with cursor).

## 5. Rate limiting and backoff (universal)

```python
async def safe_send(bot, chat_id, *args, **kwargs):
    for attempt in range(4):
        try:
            return await bot.send_message(chat_id, *args, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 0.5)
        except (TimedOut, NetworkError):
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("send failed after retries")
```

In PTB, `AIORateLimiter()` on the builder handles most of this automatically.

## 6. Logging and monitoring

```python
import logging, logging.handlers

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler("bot.log", maxBytes=10_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logger.addHandler(handler)

# Log every update with context: user id, chat id, command, outcome, latency
# Send exceptions to an admin chat AND a structured log (Sentry-ready):
try:
    ...
except Exception:
    logger.exception("update failed user=%s", update.effective_user.id)
    await notify_admins(context)
```

Health checks: expose an HTTP `/healthz` (aiogram webhook app already has aiohttp — add a route; for polling add a tiny aiohttp server on a port), log updates-per-minute, error rate, queue depth.

## 7. Testing bots

- Unit-test handlers by constructing `Update` objects from raw JSON fixtures and asserting on the mocked `Bot` calls (PTB docs cover this pattern extensively; both libs let you build fakes).
- Integration: use a **test bot** with a throwaway token and a test private chat; assert with `get_chat`/`get_my_commands` after `post_init`.
- For webhook endpoints, replay recorded update JSON with `requests`/`httpx` and assert the secret-token check works.
- Keep business logic out of handlers (handlers parse, services decide) so services are unit-testable without Telegram.

## 8. Troubleshooting table

| Symptom | Likely cause / fix |
|---|---|
| Button spins forever | `query.answer()` never called |
| No updates at all | webhook set while polling (delete_webhook) or wrong allowed_updates |
| `Bad Request: can't parse entities` | unescaped MarkdownV2 / malformed HTML — use HTML + html.escape |
| 401 Unauthorized | revoked/wrong token |
| 409 Conflict | another process polling same token — one process per token |
| `Forbidden: bot was blocked` | user blocked bot — remove from broadcast list |
| 429 | respect `parameters.retry_after`; lower broadcast rate |
| Inline query not arriving | /setinline not enabled in BotFather |
| Group messages not seen | privacy mode ON — /setprivacy or make bot admin |
| File upload fails >50 MB | use local Bot API server or Telethon (2 GB) |
| Session lost (Telethon) | use StringSession stored in env/secret manager |
| Handlers firing twice | handler registered twice / both polling and webhook |

## 9. Production checklist (final gate)

- [ ] Secrets in env/secret manager; `.env` gitignored; token revocation plan documented
- [ ] Webhook secret-token verified (or polling with one process per token)
- [ ] RetryAfter handling on all sends; broadcast rate ≤25/s
- [ ] Idempotent payment/fulfillment handlers
- [ ] DB migrations (alembic) not ad-hoc schema
- [ ] Structured logs + error → admin notification
- [ ] Graceful shutdown (SIGTERM → stop polling, flush persistence, close DB)
- [ ] Docker image pinned to exact library versions in requirements
- [ ] Health endpoint for the orchestrator
- [ ] Backup of the database + (Telethon) session
- [ ] Test bot account used for staging deploys
