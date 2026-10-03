# Research record — 2026-10-03

## Scope and method

All original repository files were read. The 13 original skills were revised and
five framework skills added, for 18 total. Research covers Telegram's official
Bot API and feature/topic guides, the selected frameworks' official documentation,
released source and package/release metadata, and the dependencies directly used
by the supplied recipes. Each skill records its own evidence in
`references/sources.md`.

This is a practical coverage audit through 2026-10-03. It does not claim to have
read every page on the web, every third-party framework, or every upstream method.
The canonical method/type reference remains authoritative for specialized fields.
Guides provide original decisions and validated examples rather than copied manuals.

## Version baseline

| Component | Baseline | Evidence / interpretation |
|---|---|---|
| Telegram Bot API | 10.3, 2026-08-24 | [Official changelog](https://core.telegram.org/bots/api#recent-changes) |
| python-telegram-bot | 22.8, 2026-06-12 | [Release](https://github.com/python-telegram-bot/python-telegram-bot/releases/tag/v22.8); wrapper does not imply all 10.3 fields |
| aiogram | 3.31.0, 2026-08-26 | [Release](https://github.com/aiogram/aiogram/releases/tag/v3.31.0); API 10.3 support |
| Telethon | 1.45.0, 2026-09-10 | [Changelog](https://docs.telethon.dev/en/stable/misc/changelog.html); installed layer 229 |
| go-telegram/bot | 1.27.0 | [Source register](../telegram-bot-go-botapi/references/sources.md) |
| gotgbot | 2.0.0-rc.36 | Release candidate is explicit, not relabeled stable |
| classic Go telegram-bot-api | 5.5.1 | Older released binding with API coverage limitations |
| gotd / contrib | 0.162.0 / 0.25.0 | [Source register](../telegram-bot-gotd-contrib/references/sources.md); actual packages and pinned module graph |
| grammY | 1.46.0, 2026-08-26 | [Release](https://github.com/grammyjs/grammY/releases/tag/v1.46.0) |
| Telegraf | 4.16.3, 2024-02-29 | [Release](https://github.com/telegraf/telegraf/releases/tag/v4.16.3); current released package can lag Bot API |
| TelegramBots / Pengrad | 10.3.0 / 10.3.0 | [Java source register](../telegram-bot-java/references/sources.md) |
| Telegram.Bot | 22.10.3.2, 2026-09-25 | [NuGet version](https://www.nuget.org/packages/Telegram.Bot/22.10.3.2); latest GitHub release list was not the newest package |
| irazasyed PHP SDK | 3.16.0, 2026-03-23 | [Release](https://github.com/irazasyed/telegram-bot-sdk/releases/tag/v3.16.0) |
| teloxide | 0.17.0 | [Rust source register](../telegram-bot-rust/references/sources.md); released source takes priority over development docs |

Other named alternatives are architectural comparison/lookup routes. They do not
all have bundled tested applications. Optional recipe dependencies and OpenAI
models are deployment selections; the pack does not invent a latest model or
claim all optional dependency versions were tested.

## Coverage improved

- Framework lifecycle, routing, context narrowing, dialogs, middleware, media,
  polling/webhooks, state, errors and migration boundaries are now explicit.
- Added JavaScript, Java, .NET, PHP and Rust skill entrypoints and original starters.
- Current Telegram routing includes Rich Messages and drafts, Business/Secretary,
  managed bots, guest mode, bot-to-bot communication, private topics, communities,
  channel direct messages, stories, suggested posts, paid media and gifts.
- Mini App guidance distinguishes launch modes, verifies signed data on the
  server, and exchanges it for scoped expiring backend sessions.
- Stars guidance separates invoice/checkout/payment/fulfillment/refund, uses an
  atomic one-time ledger, and documents recurring payment state separately.
- UI guidance checks callback bytes, ownership, current button fields and client
  support. Rich-message payloads enforce exclusive representations.
- Persistent state and outbox examples address restart, duplicate delivery,
  transaction boundaries, worker leases, stale workers and uncertain sends.
- All seven product recipes retain a concrete starting point, configuration and
  failure limitations. Missing variables, unsupported APIs and incomplete redirect
  service behavior were replaced with supplied files.

## Deliberate boundaries

Protocol/API/framework/client versions are separate facts. A live documentation
page can describe features absent from a pinned release; inspect installed source
and use a documented raw path only when needed. MTProto bot/user rights remain
distinct. Payments, auth and delivery examples cover specific tested invariants,
not certification of a deployment.

There are no standalone specialists for every smaller ecosystem (for example
Kotlin, Swift, Ruby, Scala or C++), and no end-to-end project for each specialized
Telegram API family. The fundamentals capability map supplies official lookup
routes and design boundaries. Add a specialist when a concrete task justifies it.

References are dated snapshots. Maintainers should update related guides,
manifests, tests and this matrix together after a verified release.
