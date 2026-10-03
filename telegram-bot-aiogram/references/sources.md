# aiogram source register

Checked **2026-10-03**. Baseline **aiogram 3.31.0**, released **2026-08-26**, documented Python **3.10+** / Bot API **10.3**. Package metadata requires Python `>=3.10,<3.15`; its extras include `redis` and `i18n`, but **not fastapi**. Sources were published/versioned at or before the cutoff; live pages need rechecking for future tasks.

| Canonical primary source | Verified scope |
| --- | --- |
| https://docs.aiogram.dev/en/v3.31.0/ | Async framework, Python 3.10+, API 10.3 baseline |
| https://docs.aiogram.dev/en/v3.31.0/changelog.html | 3.31.0 released 2026-08-26; API 10.3/defaults/webhook-DI fixes |
| https://docs.aiogram.dev/en/v3.31.0/migration_2_to_3.html | Legacy constructor/default/filter/model/FSM migration boundaries |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/router.html | Observers, router attachment/order, handler routing |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/magic_filters.html | F comparisons, logical composition and content predicates |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/command.html | Command versus injected CommandObject/deep links |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/filters/callback_data.html | Typed packing/filtering and byte/separator constraints |
| https://docs.aiogram.dev/en/v3.31.0/api/types/callback_query.html | Answer API, message availability and inline callback IDs |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/index.html | State transitions and cancellation patterns |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/storages.html | Memory/Redis storage and data lifetime |
| https://docs.aiogram.dev/en/v3.31.0/_modules/aiogram/fsm/storage/redis.html | Redis create_isolation and shared key builder |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/finite_state_machine/scene.html | Optional Scenes Wizard for complex flows |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/dependency_injection.html | Context data and handler parameter-name injection |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/middlewares.html | Outer/inner placement and handler short-circuiting |
| https://docs.aiogram.dev/en/v3.31.0/api/upload_file.html | FSInputFile/BufferedInputFile/URLInputFile semantics |
| https://docs.aiogram.dev/en/v3.31.0/utils/media_group.html | MediaGroupBuilder methods |
| https://docs.aiogram.dev/en/v3.31.0/api/download_file.html | Download helpers/destinations |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/dispatcher.html | feed_update and bounded polling task concurrency |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/webhook.html | aiohttp receiver/secret handling, runner and other framework adapter |
| https://docs.aiogram.dev/en/v3.31.0/utils/i18n.html | Gettext catalogs, middleware setup and lazy string boundaries |
| https://docs.aiogram.dev/en/v3.31.0/dispatcher/errors.html | ErrorEvent handling and exception types |
| https://pypi.org/pypi/aiogram/3.31.0/json | Upload date, Python requirement and extras verified directly from release metadata |
| https://core.telegram.org/bots/api | API 10.3 announcement 2026-08-24; update/file/callback/webhook constraints |
| https://apscheduler.readthedocs.io/en/3.x/userguide.html | APScheduler 3 AsyncIOScheduler, job IDs, stores/misfire/ownership decisions |

The original starter has offline checks; no Telegram or Redis connections were used for them. These establish import/configuration and selected state behavior, not permissions, delivery or deployment guarantees. See [validation record](validation.md).
