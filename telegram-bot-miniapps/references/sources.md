# Sources and compatibility ledger

Checked: **2026-10-03**. Cutoff: **2026-10-03**. References are primary documentation; claims about application sessions/rate limits are design choices in this repository.

| Primary source | Checked scope |
|---|---|
| [Telegram Mini Apps](https://core.telegram.org/bots/webapps) | Launch contexts, JS API, version gating, HMAC/Ed25519, storage, native UI and testing |
| [Launch contexts](https://core.telegram.org/bots/webapps#implementing-mini-apps) | Keyboard/inline/menu/profile/direct/inline-mode/attachment and join-request behavior |
| [Validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app) / [third-party validation](https://core.telegram.org/bots/webapps#validating-data-for-third-party-use) | Bot-token HMAC versus Ed25519 signed payload; freshness |
| [Testing](https://core.telegram.org/bots/webapps#testing-mini-apps) | Separate Telegram test server; HTTP exception applies there |
| [Bot API](https://core.telegram.org/bots/api) | **10.3, 2026-08-24**; July 14, 2026 origin-protection announcement, default July 20 with BotFather opt-out |
| [PTB WebAppInfo](https://docs.python-telegram-bot.org/en/stable/telegram.webappinfo.html) / [aiogram v3.31.0 WebAppInfo](https://docs.aiogram.dev/en/v3.31.0/api/types/web_app_info.html) | PTB stable page identified as v22.8; wrapper type references for bot entry points |
| [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/) / [security](https://fastapi.tiangolo.com/tutorial/security/first-steps/) | TestClient/HTTPX and bearer handling; the local example is not a Telegram-supplied application |
| [Python 3.12 urllib.parse](https://docs.python.org/3.12/library/urllib.parse.html#urllib.parse.parse_qsl) / [sqlite3](https://docs.python.org/3.12/library/sqlite3.html) | Strict parsing options, parameterized SQL and connection/transaction lifecycle |

Verified API milestones: SecondaryButton/BottomButton in **7.10**; fullscreen/safe areas in **8.0**; DeviceStorage/SecureStorage in **9.0**. User clients still need the corresponding WebApp API. This is a checked snapshot, not a promise of universal device support. PTB **22.8** and aiogram **3.31.0** documentation were inspected; no runtime wrapper installation is required by the local helper. Offline tests exercise Python auth/storage and in-process HTTP behavior, not Telegram network integration.

Executed offline environment: Python **3.12.1**, FastAPI **0.115.3**, Pydantic **2.9.2**, HTTPX **0.25.2**; Uvicorn **0.34.0** was present but no external server was started. These are tested installed versions, not a recommendation to choose older versions for a new deployment. Record and check your project's selected versions separately.
