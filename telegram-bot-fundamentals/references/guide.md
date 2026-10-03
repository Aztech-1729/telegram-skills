# Core implementation guide

## Identity and credentials

Create a bot through BotFather `/newbot`; configure its commands, description, profile, inline mode and relevant capabilities. Obtain application `api_id` / `api_hash` at [my.telegram.org](https://my.telegram.org) only for native Telegram client work. MTProto bot accounts still require a bot token; user accounts use the supported user-login flow and protected session storage.

Use `TELEGRAM_BOT_TOKEN` consistently in new pack examples. Existing projects may keep another convention. A `.env` file needs an explicit loader; setting an environment variable and merely creating `.env` are different actions.

```text
bot-project/
  application entrypoint and configuration
  handlers/       transport and update dispatch
  services/       application decisions and integrations
  storage/        repositories, transactions and migrations
  tests/          behavior and boundary cases
```

Keep `.env`, user sessions, local databases, downloaded files, and build outputs out of the application's repository. Never place a bot token in the webhook path or application logs.

## Update delivery and routing

Choose polling for a simple continuously running worker, or webhooks when the deployment already supports a reachable HTTP endpoint. Delete an existing webhook deliberately before starting polling. Avoid automatically discarding pending updates during restarts; that is a data-loss decision.

Webhook handlers validate `X-Telegram-Bot-Api-Secret-Token`, constrain body size, parse an Update, and accept it into durable processing before acknowledging when the task requires reliable delivery. Acknowledge quickly; slow external work belongs in a bounded worker/queue. Use a unique bot/update key for replay handling. Polling offsets and webhook delivery are transport acknowledgments, not proof that an order or job finished.

| Incoming interaction | Route and implementation concern |
| --- | --- |
| Command / text / media | Message handler; commands may include `@botusername`; distinguish edits and channel posts. |
| Inline button | Callback query; acknowledge first, then validate payload and ownership. |
| Inline search | Inline query; use stable result IDs and appropriate personalized caching. |
| Membership / join request | Explicit update subscriptions and relevant bot administrator rights. |
| Poll answers / reactions | Use update-specific identities; anonymous or aggregate updates differ from per-user updates. |
| Stars purchase | Pre-checkout validation followed by successful-payment processing; invoice issuance is not payment completion. |
| Business connection | Track connection lifecycle and latest rights; route business messages separately. |
| Managed / guest bot / stopped generation | Subscribe and parse the specific update, then use its correct scoped context. |

Privacy mode governs which group messages bots receive. A command menu does not change privacy mode or authorize execution. Users normally initiate a private-chat interaction before a bot can message them; store known chat IDs from observed interactions rather than trying to enumerate all users.

## Requests, types and formatting

Raw HTTP uses methods such as `getMe`, `sendMessage`, `setWebhook`; Python wrappers commonly use snake_case. Inspect the exact chosen SDK signature and current response object.

The response envelope has `ok` and result/error information. Preserve machine-readable `error_code` and `parameters` for decisions, and sanitize transport errors containing token-bearing URLs. Store chat/user IDs in suitable integer types; negative chat IDs are meaningful. Entity offsets use UTF-16 units; escaping and splitting must preserve valid formatting. Prefer plain text when a parse mode provides no benefit.

Reuse Telegram `file_id` when available. A hosted Bot API file workflow, URL fetch, local Bot API server, and MTProto transfer have different restrictions; check the selected method instead of applying one universal upload limit. See [local server](https://core.telegram.org/bots/api#using-a-local-bot-api-server) and the advanced guide for migration.

## State, rates and permissions

Use database transactions for orders, entitlements, score awards, and jobs. Dialog/session state is not a replacement for a durable ledger. Decide whether state is scoped per user, chat, topic or connection; choose conflict handling before enabling parallel processing.

Queue broadcasts; bound concurrency and account for per-chat as well as overall limits. Respect `retry_after` and stop messaging unreachable/blocked users. Treat paid broadcasting as an explicitly budgeted feature; never enable paid sending as an implicit retry tactic.

For moderation, verify actor and bot administrator capabilities, target membership, chat type, and permitted scope. For downloads, constrain accepted hosts/files, time/resource limits and subprocess arguments. For Mini Apps, authenticate on the backend; never trust `initDataUnsafe` as proof of identity.

## Delivery checklist

- Registered commands and handlers match the intended update types; callback queries get answered.
- Required secrets/configuration fail clearly at startup without revealing their values.
- Restart, duplicate update, expired callback and failed delivery behavior are defined.
- DB transactions and async work do not block unrelated updates.
- Deployment has a single transport, graceful shutdown, observable failures and recoverable state.
- Version-sensitive functionality has a confirmed SDK path or a tested raw HTTP adapter.

Primary references: [Bot API](https://core.telegram.org/bots/api), [FAQ](https://core.telegram.org/bots/faq), [Bot features](https://core.telegram.org/bots/features).
