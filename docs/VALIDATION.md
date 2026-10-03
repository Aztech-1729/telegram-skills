# Validation record — 2026-10-03

## Scope

Checks use synthetic updates, fake transports and temporary databases. They do
not authenticate Telegram clients, register webhooks, purchase Stars, send messages
or call OpenAI. A successful compilation or offline test does not establish live
Telegram rendering, delivery, deployment or production readiness.

## Local checks

Result: **49 Python behavioral tests and two JavaScript transport tests passed**.
All 18 skill entrypoints pass the package structure/link/syntax check. The separate
skill-creator validator is also run for every entrypoint before publication.

| Area | Validation |
|---|---|
| All 18 skills | Frontmatter/name/description, linked resources and skill-creator validation |
| Source pack | Local Markdown paths/anchors, Python AST, JSON/TOML/XML/YAML parsing, whitespace and credential-pattern scan |
| PTB / aiogram / Telethon | Actual pinned packages, synthetic handlers, callback ownership, configuration and API constructors |
| Mini App | HMAC tampering/freshness/duplicates, scoped expiring sessions, HTTP requests, ownership and persistent todo data |
| Stars | Atomic credit/receipt writes, duplicate concurrent receipts, rollback, persistence and refund bookkeeping |
| Advanced operations | Leased outbox, stale-worker fencing, uncertainty, retry bounds, webhook secrets and SQLAlchemy lifecycle |
| UI / Rich Messages | UTF-8 callback bounds, UTF-16 entities, pagination and exclusive rich payloads |
| Recipes | Failed-send persistence, quiz ownership/expiry/replay/concurrent scoring, warning scope, authorization before writes and URL schemes |
| JavaScript | grammY and Telegraf commands/callbacks through a local fake Bot API server |
| Go | Five starter applications compiled against pinned module graphs |
| Java | TelegramBots starter compiled using published jars with Java 17 language target |
| .NET / PHP / Rust | Source/API and manifest review; required compiler/interpreter unavailable locally |

The paid Mini App forward-test independently exercised fresh sessions after
reopening, duplicate payments, buyer/price mismatch, cross-user deletion and
refund bookkeeping. It identified an integration gap: a public authenticated-user
helper was added so checkout routes can use the verified session identity.

## Repeat Python checks

Use Python 3.11+ for the pack validator (it uses `tomllib`); individual starters
document their runtime requirements. From repository root:

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_pack.py
python scripts/run_offline_checks.py
```

The runner gives each example its own process because different starter folders
contain modules with the same name. Optional live recipe dependencies such as
OpenAI, feedparser and yt-dlp are not invoked by these tests.

## Repeat JavaScript checks

From `telegram-bot-javascript/assets/starter`:

```sh
npm ci --ignore-scripts
npm test
```

Tests bind a loopback HTTP server. They never use api.telegram.org.

## Build checks

Each Go starter has a `go.mod`/`go.sum`; run `go build ./...` in each asset
directory. The Java project has a Maven `pom.xml`; run `mvn package` from its
`assets/echo` directory. Use `dotnet build` for the .NET project, `php -l webhook.php`
and `composer install` for PHP, and `cargo check` for Rust in their asset directories.
The [workflow template](validate-workflow.yml) defines those checks. It was not
activated because the publishing token lacks GitHub's separate `workflow` scope.
A maintainer can place it at `.github/workflows/validate.yml` using a credential
with that permission. No remote workflow run is claimed by this audit.

## Remaining live checks

Use a development bot to check transport setup, real permissions, rendering and
client feature support. Exercise actual payment/renewal/refund flows only in the
appropriate development environment. Test proxy/TLS/worker restarts and observe
backpressure in the chosen deployment. Downloader egress and resource isolation,
external feed behavior and AI model/account availability require separate checks.

The included SQLite examples target a single persistent host. A distributed
deployment needs a database/queue design suited to multiple workers. Recurring
Stars access is a documented lifecycle; the bundled ledger intentionally handles
one-time credit orders and does not implement renewals.
