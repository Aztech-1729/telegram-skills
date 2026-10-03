# Primary sources and cutoff

Checked **2026-10-03**.

| Source | Verified scope |
| --- | --- |
| [grammY 1.46.0 release](https://github.com/grammyjs/grammY/releases/tag/v1.46.0) | Release 2026-08-26; dated library baseline. |
| [Telegraf 4.16.3 release](https://github.com/telegraf/telegraf/releases/tag/v4.16.3) | Release 2024-02-29; stable release baseline, not latest Bot API parity. |
| [grammY getting started](https://grammy.dev/guide/getting-started) | Bot, handlers and polling setup. |
| [API](https://grammy.dev/guide/api) | Convenience API, raw request shapes and types. |
| [Middleware](https://grammy.dev/guide/middleware) | Ordered async middleware. |
| [Sessions](https://grammy.dev/plugins/session) | State keys/storage. |
| [Conversations](https://grammy.dev/plugins/conversations) | Replay/external operations. |
| [Runner](https://grammy.dev/plugins/runner) | Parallel processing and serialization. |
| [Errors](https://grammy.dev/guide/errors) | Error boundaries. |
| [Transports](https://grammy.dev/guide/deployment-types) | Polling/webhook deployment. |
| [Auto-retry](https://grammy.dev/plugins/auto-retry) | Bounded optional retries. |
| [Telegraf](https://telegraf.js.org/) | Current v4.16.3 entrypoint, handlers and webhook setup. |

Plugin packages need independent version checks; a core framework baseline does not lock every plugin API.
