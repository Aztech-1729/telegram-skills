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
| [Telegraf](https://telegraf.js.org/) | Project documentation; hosted TypeDoc pages can describe an older API, so verify signatures against the pinned source below. |

Plugin packages need independent version checks; a core framework baseline does not lock every plugin API.

## Focused lifecycle/routing audit: 2026-10-04

- [grammY Bot source at 1.46.0](https://github.com/grammyjs/grammY/blob/v1.46.0/src/bot.ts): polling setup, shutdown promise and final offset confirmation.
- [grammY Context source](https://github.com/grammyjs/grammY/blob/v1.46.0/src/context.ts): source-topic and direct-message topic routing in reply shortcuts.
- [Telegraf receiver source at 4.16.3](https://github.com/telegraf/telegraf/blob/v4.16.3/src/telegraf.ts): launch callback timing, stop-before-start behavior, handlerTimeout and webhook catch boundary.
- [Telegraf Context source](https://github.com/telegraf/telegraf/blob/v4.16.3/src/context.ts): reply topic propagation.
- The sessions, conversations, runner and error guides above were reread for state/replay/error distinctions.

Both expanded starter tests passed with a local fake API on 2026-10-04. Entry modules passed Node syntax checks. No real receiver, webhook or Telegram request ran; startup signal races and durable storage remain application checks. This focused review does not advance unrelated release/plugin baselines.

## Conversation comparison follow-up: 2026-10-04

The official conversations/session guides above were reread for inner/outer
contexts, replayed API operations, external results, storage/version keys and
update-driven wait expiry. The installed `@grammyjs/conversations` **2.1.1**
package metadata and declarations were checked independently of grammY 1.46.0.
Five new fake-transport tests exercise the feedback factory. Production
persistence and cross-process recovery remain application checks.
