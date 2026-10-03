# Sources and compatibility ledger

Checked: **2026-10-03**. Cutoff: **2026-10-03**. Primary documentation. Design choices such as inbox/outbox schemas, lease policy and retry budget are original repository guidance.

| Primary source | Checked scope / baseline |
|---|---|
| [Bot API](https://core.telegram.org/bots/api) | **10.3, 2026-08-24**; update transport, webhook secrets, local server capabilities |
| [Bot FAQ](https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this) | Approximate per-chat/group/global limits and paid-broadcast caveats |
| [Official local server](https://github.com/tdlib/telegram-bot-api) / [local mode](https://core.telegram.org/bots/api#using-a-local-bot-api-server) | Hosted/local migration and file/network limits |
| [SQLAlchemy 2 async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) / [SQLite upsert](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict-upsert) | Declarative base, per-task sessions, engine disposal and dialect-specific conflict strategy |
| [PTB JobQueue v22.8](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.jobqueue.html) | `job-queue` extra, timezone/weekdays, async callbacks |
| [PTB AIORateLimiter](https://docs.python-telegram-bot.org/en/stable/telegram.ext.aioratelimiter.html) | Page identified as **v22.8**; `rate-limiter` extra, default zero retries, reference implementation scope |
| [aiogram webhook v3.31.0](https://docs.aiogram.dev/en/v3.31.0/dispatcher/webhook.html) / [FSM storages](https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/storages.html) | Secret validation, background acknowledgment, Redis state |
| [APScheduler 3 user guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) / [asyncio scheduler](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/asyncio.html) | Explicit **3.x** API family; persistence/misfire/coalescing and scheduler lifecycle; no claim about latest release |
| [Docker build guidance](https://docs.docker.com/build/building/best-practices/) / [nginx proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) | Image pinning/context/secrets and proxy directives; infrastructure fragments need adaptation |

Local behavior validation: Python **3.12.1**, SQLAlchemy **2.0.36**, aiosqlite **0.20.0**. Outbox/retry/secret helper uses the standard library; async state example adds the two dependencies above. This matrix describes the executed offline environment, not recommended latest versions. No Telegram calls, paid broadcasts, container builds, webhook registration or infrastructure deployment were performed.
