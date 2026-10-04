# Node.js implementation guide

## Dependency and runtime choices

Pin a supported framework version and keep the lockfile. Match ESM/CommonJS imports to the project's package settings. The supplied assets are ESM JavaScript. TypeScript projects should model custom context explicitly; grammY exports Bot API types through `grammy/types`. Use Node, Deno or an edge platform only when the framework and all selected plugins/storage/HTTP adapters support that runtime.

## Middleware and handlers

Register authentication/context enrichment before protected actions. Register command/action-specific handlers before broad text/callback fallbacks. In grammY use `bot.command`, narrowed `bot.on` queries, `bot.callbackQuery`, `ctx.reply`, `ctx.answerCallbackQuery`, and `ctx.api` for general operations. In Telegraf use `bot.command`, the `telegraf/filters` filters, `bot.action`, `ctx.reply`, `ctx.answerCbQuery`, and `ctx.telegram`.

Middleware can stop propagation; `await next()` is necessary when later handlers should run. Do not call it twice or leave asynchronous work detached without a durable owner. Catch errors at the intended boundary; logging the exception's raw request URL may reveal the token. See [grammY middleware](https://grammy.dev/guide/middleware) and [Telegraf reference](https://telegraf.js.org/).

## State and dialog flows

Use grammY session middleware for scoped dialog data, with a fresh initial object per session and a chosen persistent storage adapter when restarts matter. Put purchases, entitlements, shared resources and audit records in transactional application storage. Telegraf sessions are likewise separate from durable business records; Scenes/Stage/Wizard are dialog abstractions, not a database.

When using grammY conversations, understand replay and use the documented external operation boundary for database/network reads or side effects. Persist conversation state only through a supported adapter and version migrations; conversations-plugin versions have their own compatibility constraints. Read [sessions](https://grammy.dev/plugins/session) and [conversations](https://grammy.dev/plugins/conversations) when those modes apply.

Parallel updates can lose session changes unless conflicting keys are serialized. grammY runner's concurrency should be combined with `sequentialize` based on the same session/resource keys. Multiple processes need a cross-process design or database transactions; an in-process lock is insufficient. Read [runner](https://grammy.dev/plugins/runner) and [scaling](https://grammy.dev/advanced/scaling).

## Keyboards, inline mode and media

Use framework keyboard builders or correctly shaped raw reply markup. Callback data should contain a compact action/resource identifier; authorize and validate on receipt. Separate inline result cache policy from ordinary message state. Enable inline mode in BotFather.

grammY `InputFile` wraps actual upload sources; Telegraf accepts documented file descriptors/Input helpers. A URL, stored file ID and filesystem stream are different inputs. Close files/streams and bound external downloads; use cached file IDs when suitable. Dynamic formatted text needs context-appropriate escaping. Large-message splitting must preserve entities and code blocks.

## Polling, webhooks and deployment

For polling, delete/migrate a webhook deliberately and run one reception owner per bot token. The assets do not automatically discard queued updates. Stop cleanly on termination and ensure the host restarts only after the worker exits.

For grammY webhooks, choose the documented `webhookCallback` adapter for the HTTP platform. For Telegraf use its documented webhook launch/createWebhook integration. Configure a dedicated secret token, bounded payloads, a public HTTPS endpoint where required and a stable startup strategy. Reuse a bot instance in serverless handlers, but avoid shared mutable request state. Webhook acknowledgment and durable side-effect completion are separate milestones. See [transport comparison](https://grammy.dev/guide/deployment-types).

## Errors, throttling and newer Bot API fields

grammY distinguishes API errors, HTTP failures and handler errors; `bot.catch` is the polling-handler boundary, while HTTP applications own their request error boundary. Auto-retry is optional and must use bounded policy appropriate to the method. Rate-limit-user middleware is not the same as outbound Telegram pacing. See [errors](https://grammy.dev/guide/errors) and [auto-retry](https://grammy.dev/plugins/auto-retry).

For a new feature, inspect the installed API types and current schema. grammY's `api.raw` uses object-shaped parameters for known methods; it is not a guarantee that every future method exists in that installed version. Telegraf's `telegram.callApi` is its lower-level request path, but typed/generated support can still lag. Use a validated HTTP adapter if a required method is absent, preserving error envelopes and multipart rules.

## Verification scope

`npm test` covers synthetic `/start`, topic-aware plain-text echoes, chat/inline/stale callback acknowledgment, ignored edits/media and absence of real Telegram transport. Check shared-state concurrency, webhook secret/replay and graceful termination in the actual application. Use [diagnostics](troubleshooting.md) for pinned lifecycle/error boundaries. Live client rendering and deployment are separate checks.
