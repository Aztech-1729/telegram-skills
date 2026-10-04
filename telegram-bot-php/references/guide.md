# PHP implementation guide

## Dependency and project setup

Use Composer and commit the application lockfile. The checked SDK baseline is 3.16.0; the 3.x installation guide requires PHP 8.0+, while a chosen Laravel release can require a higher version. Configure environment values through the host's actual configuration system. In Laravel, use the registered provider/facade/config and account for configuration caching; do not read changing environment variables ad hoc throughout application logic. See [installation](https://telegram-bot-sdk.com/docs/getting-started/installation/) and [initialization](https://telegram-bot-sdk.com/docs/getting-started/initialize/).

## SDK selection boundaries

The irazasyed SDK's `Api` is a request/client facade; use its supported arrays/objects and `BotsManager` when selecting configured bots. Map each update to the correct bot configuration. In Longman projects, use `Longman\TelegramBot\Telegram` and its request/command architecture; database and long-poll examples belong to that project. Avoid copying one library's webhook input handling into another. See [Longman project](https://github.com/php-telegram-bot/core).

## Updates and commands

Webhook delivery and getUpdates polling are mutually exclusive. A polling application owns its persisted offset and background process; do not run a tight unbounded loop inside a web request. The SDK's `getWebhookUpdate()` represents the current Update, not a batch of all pending updates.

Command classes and routing can be useful for modular applications. Keep commands small, move application decisions into services, and check authorization from current Telegram rights and the application's ownership rules. Dispatch callbacks, inline queries and payments separately when a command pipeline does not handle them. Do not dereference a message field on every update. See [commands](https://telegram-bot-sdk.com/docs/guides/commands-system/) and [updates](https://telegram-bot-sdk.com/docs/guides/webhook-updates/).

## Webhook and Laravel host integration

Use a dedicated random secret supplied during webhook registration. Compare `X-Telegram-Bot-Api-Secret-Token` with a constant-time comparison before parsing accepted work. The historical upstream guide suggests including a token in the URL; the pack instead keeps credentials out of public routes/logs. Validate body size/JSON/object shape and allow only the expected HTTP method.

Exclude only the specific webhook endpoint from browser-oriented CSRF middleware where necessary, using the selected Laravel release's actual configuration API. Leave browser/administrative routes protected. A secret header proves transport membership, not permission for a user's callback/admin command. Durable side effects need bot/update-key uniqueness, a transaction and a queue; do not acknowledge an update before accepting the work the application cannot afford to lose.

## Files, markup and current features

Use documented upload input wrappers/streams; a filesystem path, multipart body, URL and reusable Telegram file ID have different handling. Close streams and constrain external downloads. Escape dynamic HTML with the correct encoding or send plain text. Request objects/SDK method aliases must match the installed release.

The PHP SDK baseline does not establish automatic Bot API 10.3 coverage. For a missing method/field, inspect package source first, then use a supported raw API request or a separate tested HTTP adapter. Preserve the `ok`/error/parameters envelope, JSON/multipart distinctions and retry information. Do not invent a magic method merely because the wire API has a similarly named endpoint.

## Reliability and testing

Keep business records in transactions rather than PHP memory. Scope sessions per bot/user/chat/topic as appropriate; workers across processes need shared storage. Queue jobs with bounded retries; treat timeout-after-send as an uncertain outcome. Log error classes/codes and correlation IDs rather than full token-bearing URLs or user payloads.

Validate with Composer dependency resolution, `php -l`, fixtures for valid/invalid secrets, malformed updates and duplicate handling, plus application tests for authorization and durable processing. The starter is a constrained echo example and does not include an order ledger, worker queue or completed hosting configuration.

`php test.php` checks the extracted WebhookInput.php boundary with no SDK/client. The endpoint copies forum and direct-message topic IDs into the plain-text send request. The fixture suite checks incorrect method/secret, oversized/invalid JSON, invalid numeric IDs and ignored non-message/edit updates. It does not implement deduplication. The 2026-10-04 local audit could not execute PHP: no installed runtime, and the official portable download failed certificate validation. Native lint/test results are recorded separately.

Use [diagnostics](troubleshooting.md) for SDK return-shape corrections, configuration caching, worker retries and raw-method fallback.
