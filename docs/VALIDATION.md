# Validation record — 2026-10-03

## Scope

Offline checks use synthetic updates, fake transports and temporary databases.
Hosted validation additionally checks public documentation/package endpoints and,
on the default branch when configured, authenticates a dedicated Telegram test bot
with read-only `getMe`. It does not register webhooks, purchase Stars, send messages,
read chat history or call OpenAI. A successful build or check does not establish
live Telegram rendering, delivery, deployment or production readiness.

## Hosted validation

The active [validation workflow](../.github/workflows/validate.yml) runs on pushes,
pull requests, manual dispatch and Mondays at 04:17 UTC. The
[recorded successful run](https://github.com/Aztech-1729/telegram-skills/actions/runs/37125986130)
passed **all 13 jobs**: checks across seven languages, five independent Go builds,
49 Python behavioral tests, two JavaScript transport tests, the then-current
maintenance test suite, 14 public HTTP checks and dedicated-bot `getMe`.
The root maintenance suite is extended as automation changes; its current result
and count are reported by the workflow rather than fixed here.

| Hosted area | What passed |
|---|---|
| Python / JavaScript | Pack validation, isolated behavioral tests, maintenance tests, fake-server transport tests and Mini App JavaScript syntax |
| Go | Dependency checksum verification and compilation of all five starters |
| Java | Maven verification using Java 17 |
| .NET | Release build using .NET 8 |
| PHP | Composer manifest validation, dependency installation, PHP lint and SDK class loading |
| Rust | `cargo check` with the runner's stable toolchain |
| Public online | Fourteen documentation and package endpoints returned the expected response shape |
| Telegram | `getMe` authenticated the dedicated test bot without sending messages or changing bot state |
| Required gate | The final `validation` job confirmed that every applicable job succeeded |

Pull requests do not receive `TELEGRAM_TEST_BOT_TOKEN`. The Telegram job is skipped
outside the default branch and on pull requests. When the secret is absent, its
script reports an explicit skip; a malformed token or failed authentication fails
the job. The final gate permits the deliberately skipped job, so a green badge
alone is not evidence that authenticated Telegram checks ran. Inspect its summary.

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
| .NET / PHP / Rust | Source/API and manifest review locally; builds/lint/SDK loading subsequently passed in hosted validation above |

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
python -m unittest discover -s tests -p 'test_*.py'
```

The example runner gives each starter its own process because different folders
contain modules with the same name. Root tests cover maintenance behavior and
online-check failure paths using controlled inputs. Optional live recipe
dependencies such as OpenAI, feedparser and yt-dlp are not invoked by these tests.

## Repeat JavaScript checks

From `telegram-bot-javascript/assets/starter`:

```sh
npm ci --ignore-scripts
npm test
```

Tests bind a loopback HTTP server. They never use api.telegram.org.

## Build checks

Each Go starter has a `go.mod`/`go.sum`; run `go build ./...` in each asset
directory. The Java project has a Maven `pom.xml`; run `mvn verify` from its
`assets/echo` directory. Use `dotnet build` for the .NET project, `php -l webhook.php`
and `composer install` for PHP, and `cargo check` for Rust in their asset directories.
The active [workflow](../.github/workflows/validate.yml) records exact toolchain
setup and additional manifest/checksum checks. Dependency resolution may contact
package registries; compiling the examples does not execute a live bot.

## Repeat online checks

The public check needs no credentials:

```sh
python scripts/check_online.py --report online-checks.json
```

It checks reachability and expected response shape, with bounded retries. It does
not verify every API claim or prove that a wrapper implements every Telegram
capability. Daily source monitoring separately compares normalized content hashes
and release versions; see [upstream status](UPSTREAM_STATUS.md) and the
[automation guide](AUTOMATION.md).

For the optional authentication check, configure `TELEGRAM_TEST_BOT_TOKEN` as an
Actions repository secret containing a dedicated test-bot token, then run the
validation workflow on the default branch. No token belongs in a file or command
argument. Locally, the same script reads only its environment:

```sh
python scripts/telegram_smoke.py
```

The smoke check calls only `getMe` and does not log credentials or bot identity.
An expired or revoked secret needs replacement; an unavailable service can cause
a failure without any code regression.

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
