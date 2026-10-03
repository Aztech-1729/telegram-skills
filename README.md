# Telegram Skills

[![Validate skill pack](https://github.com/Aztech-1729/telegram-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/Aztech-1729/telegram-skills/actions/workflows/validate.yml)
[![Refresh upstream evidence](https://github.com/Aztech-1729/telegram-skills/actions/workflows/upstream-refresh.yml/badge.svg)](https://github.com/Aztech-1729/telegram-skills/actions/workflows/upstream-refresh.yml)

**18 focused skills for AI agents building Telegram bots and Mini Apps across
Python, Go, JavaScript/TypeScript, Java, .NET, PHP and Rust.**

Choose a framework, load the feature skills needed for the task, then use the
linked reference and starter. Each skill has concise activation metadata,
practical implementation guidance and a dated primary-source register.

**Documentation review:** 2026-10-03 · **Telegram baseline:** Bot API 10.3
· [Research and versions](docs/RESEARCH.md) · [Validation and limits](docs/VALIDATION.md)
· [Upstream observations](docs/UPSTREAM_STATUS.md) · [Automation](docs/AUTOMATION.md)

Validation is active on pushes, pull requests and a weekly schedule. Daily source
checks refresh observed hashes and release versions; eligible dependency updates
can merge after required validation. A daily Codex maintenance agent reviews
changed documentation, adapts examples for major upgrades and repairs failing
updates, with independent review and validation before merge. Source observations
and actual content review remain separate records.

## Start here

| You need to… | Open first |
|---|---|
| Choose Bot API vs MTProto, identity or deployment approach | [Fundamentals](telegram-bot-fundamentals/SKILL.md) |
| Work in an existing project | Its [framework skill](#framework-skills), preserving the chosen stack |
| Build a particular bot product | [Recipes](telegram-bot-recipes/SKILL.md) |
| Add a web interface | [Mini Apps](telegram-bot-miniapps/SKILL.md) |
| Sell digital goods or paid access | [Stars payments](telegram-bot-payments-stars/SKILL.md) |
| Make a reliable deployed service | [Advanced features](telegram-bot-advanced-features/SKILL.md) |

### Agent workflow

1. Identify the existing language/framework, bot or user identity, chat contexts
   and requested outcome. Choose a framework only when the project has none.
2. Read the selected `SKILL.md`. Read fundamentals when protocol, identity,
   permissions or update delivery need a decision.
3. Follow its links to the reference sections relevant to the request. Add
   feature skills from the table below; load extra resources when needed.
4. Inspect the installed dependency version before copying a starter. A current
   Telegram method may be missing from an older wrapper or client.
5. Implement the requested behavior, run relevant offline checks, and report
   which live behavior still needs a development bot or client.

Example instruction for an agent that can read this checkout:

```text
Use this repository's telegram-bot-aiogram and telegram-bot-payments-stars
skills to add a one-time Stars purchase to the existing aiogram application.
Read their SKILL.md files and relevant references, preserve the current
project structure, and validate duplicate payment delivery offline.
```

Skill folders can be discovered by compatible agents through their `name` and
`description` frontmatter. If the host does not support skill discovery, provide
the paths explicitly; ordinary Markdown reading works too.

## Framework skills

| Language / protocol | Skill | Use when |
|---|---|---|
| Python · HTTP Bot API | [telegram-bot-python-telegram-bot](telegram-bot-python-telegram-bot/SKILL.md) | PTB applications, handlers, conversations, JobQueue or webhooks |
| Python · HTTP Bot API | [telegram-bot-aiogram](telegram-bot-aiogram/SKILL.md) | aiogram 3 routers, filters, FSM, middleware or DI |
| Python · MTProto | [telegram-bot-telethon](telegram-bot-telethon/SKILL.md) | Telethon bot/user sessions, history, events and raw requests |
| Go · HTTP Bot API | [telegram-bot-go-botapi](telegram-bot-go-botapi/SKILL.md) | go-telegram/bot, gotgbot or classic telegram-bot-api |
| Go · MTProto | [telegram-bot-gotd](telegram-bot-gotd/SKILL.md) | gotd authentication, peers, dispatch and recovery |
| Go · MTProto support | [telegram-bot-gotd-contrib](telegram-bot-gotd-contrib/SKILL.md) | Verified gotd/contrib persistence and support packages |
| JavaScript / TypeScript · HTTP | [telegram-bot-javascript](telegram-bot-javascript/SKILL.md) | grammY or Telegraf middleware, sessions and receivers |
| Java · HTTP | [telegram-bot-java](telegram-bot-java/SKILL.md) | TelegramBots or Pengrad project integration |
| C# / .NET · HTTP | [telegram-bot-dotnet](telegram-bot-dotnet/SKILL.md) | Telegram.Bot events, polling, ASP.NET webhooks and lifecycle |
| PHP · HTTP | [telegram-bot-php](telegram-bot-php/SKILL.md) | irazasyed SDK, Laravel integration or Longman architecture |
| Rust · HTTP | [telegram-bot-rust](telegram-bot-rust/SKILL.md) | teloxide dispatch, dialogue state and async ownership |

Bot API frameworks and MTProto clients are separate protocol choices. MTProto
requires an API ID/hash and a session as well as the appropriate bot/user
authorization. It does not grant a bot unrestricted user-account capabilities.

## Feature and product skills

| Skill | Capability | Useful resources |
|---|---|---|
| [telegram-bot-fundamentals](telegram-bot-fundamentals/SKILL.md) | BotFather, identity, transport, updates, rights, state, limits and capability routing | Planning guide and current Telegram capability map |
| [telegram-bot-keyboards-ui](telegram-bot-keyboards-ui/SKILL.md) | Inline/reply keyboards, callbacks, navigation, inline mode and deep links | UI helpers and callback/format tests |
| [telegram-bot-rich-messaging](telegram-bot-rich-messaging/SKILL.md) | Safe formatting, Rich Messages, structured reports, drafts and final persistence | Payload builders and streaming lifecycle |
| [telegram-bot-miniapps](telegram-bot-miniapps/SKILL.md) | Launch modes, WebApp SDK, signed authentication and backend-owned data | Runnable todo frontend/backend and auth tests |
| [telegram-bot-payments-stars](telegram-bot-payments-stars/SKILL.md) | Invoices, checkout, atomic one-time fulfillment, refunds and recurring-access design | Durable SQLite ledger and duplicate/rollback tests |
| [telegram-bot-advanced-features](telegram-bot-advanced-features/SKILL.md) | Persistent state, webhooks, queues, retries, deployment and observability | Leased outbox, bounded retry and SQLAlchemy examples |
| [telegram-bot-recipes](telegram-bot-recipes/SKILL.md) | Moderation, reminders, quiz, RSS, AI, media downloader and URL shortener | Seven selectable modes, database store and redirect service |

### Common task bundles

| Request | Load |
|---|---|
| Menu or catalog bot | Chosen framework + keyboards-ui + rich-messaging |
| Store with digital purchases | Framework + payments-stars + rich-messaging; advanced-features for fulfillment jobs |
| Paid Mini App | Framework + miniapps + payments-stars; share backend user/entitlement identity |
| AI assistant with live drafts | Framework + recipes + rich-messaging streaming reference |
| Group moderation or quiz | Framework + recipes + keyboards-ui as needed |
| Persistent notifications / RSS | Framework + recipes + advanced-features for durable dispatch |
| History/media workflow using MTProto | Telethon or gotd; gotd-contrib for its actual support packages |
| Business/Secretary, managed bots, guest mode, stories or channel direct messages | Fundamentals capability map + framework; inspect current method/rights before adapting |

Business/Secretary connections, managed bots, guest mode, bot-to-bot
communication, private topics, communities, channel direct messages, stories,
suggested posts, gifts and paid media have implementation decision guides and
official lookup routes in the [capability map](telegram-bot-fundamentals/references/api-capabilities.md).
They do not each have an end-to-end starter in this pack.

## Get the pack

This repository is public:

```sh
git clone https://github.com/Aztech-1729/telegram-skills.git
cd telegram-skills
```

Read the skills directly from the clone, or copy the selected complete folders
into the skill directory supported by your agent host. Keep their `references/`,
`assets/` and `scripts/` resources together. Sibling links need the corresponding
sibling skills; copying all 18 folders preserves every local route. Do not copy
only `SKILL.md` and expect the supporting files to be available.

For Codex, user skills conventionally live under `~/.codex/skills` (or the
configured `CODEX_HOME/skills`). Copy selected folders there only if local
installation is wanted. Other hosts have their own discovery conventions;
this repository does not require a particular runtime to read its instructions.

## Repository layout

```text
README.md                         Catalog, task routing and setup
docs/RESEARCH.md                   Dated baselines, sources and coverage boundaries
docs/VALIDATION.md                 What was checked and how to repeat it
docs/AUTOMATION.md                 Schedules, permissions and review procedure
docs/AGENT_MAINTENANCE.md           Daily Codex content review and repair runbook
docs/UPSTREAM_STATUS.md            Generated source changes, failures and versions
automation/sources.json            Allowed official destinations and release feeds
automation/upstream-state.json     Observed hashes and unresolved source changes
scripts/validate_pack.py           Pack structure, links, syntax and secret checks
scripts/run_offline_checks.py      Isolated offline behavior suites
scripts/check_upstream.py          Refresh source observations and generated reports
scripts/agent_maintenance.py       Plan, acknowledge reviews and guard immediate merges
.github/workflows/                 Active validation and maintenance workflows
.github/dependabot.yml             Weekly updates across eight ecosystems
telegram-bot-*/
  SKILL.md                        Activation and essential workflow
  references/guide.md              Detailed implementation decisions
  references/sources.md            Primary sources and version notes
  references/upstream-status.md    Generated observations for this skill
  assets/ or scripts/             Starters or deterministic helpers, where useful
```

Every skill has `SKILL.md`, a guide and a source register. Extra resources are
supplied only where they serve an implementation or validation task. The pack is
instructional source plus reusable examples; it is not a single deployed bot.

## Versions and example readiness

| Family | Reviewed baseline |
|---|---|
| Telegram | Bot API 10.3 · 2026-08-24 |
| Python | PTB 22.8 · aiogram 3.31.0 · Telethon 1.45.0 |
| Go HTTP | go-telegram/bot 1.27.0 · gotgbot 2.0.0-rc.36 · classic 5.5.1 |
| Go MTProto | gotd 0.162.0 · contrib 0.25.0 |
| JavaScript | grammY 1.46.0 · Telegraf 4.16.3 |
| Java | TelegramBots 10.3.0 · Pengrad 10.3.0 |
| .NET | Telegram.Bot 22.10.3.2 |
| PHP | irazasyed SDK 3.16.0; Longman documented as a separate architecture |
| Rust | teloxide 0.17.0 stable |

These are reviewed pins, not a promise that every wrapper exposes Bot API 10.3.
Versioned source, release tags and package metadata are used when live docs track
development. The [research record](docs/RESEARCH.md) explains those distinctions.

Starters contain actual entrypoints and dependency manifests. Guides identify
configuration, database and deployment assumptions. Offline tests cover selected
behavior; build-only and source-reviewed examples are explicitly distinguished in
the [validation record](docs/VALIDATION.md). The
[successful hosted run](https://github.com/Aztech-1729/telegram-skills/actions/runs/37125986130)
passed all 13 jobs across seven languages, including five Go builds, 49 Python
behavioral tests, two JavaScript transport tests, maintenance tests, 14 public
HTTP checks and read-only `getMe` authentication with a dedicated test bot.
It did not test live message delivery, payments or deployment.

## Working rules

- Keep tokens, API hashes, webhook secrets and MTProto sessions outside version
  control; use separate development credentials for live verification.
- Choose one polling/webhook receiver per token and persist important state before
  acknowledging work that must survive a restart.
- Validate Mini App data on the backend. Buttons, menus and client-provided user
  IDs do not authorize actions.
- Deduplicate updates/payment receipts and make fulfillment atomic. An ambiguous
  send timeout may already have created a message; retries need a defined policy.
- Check actual membership, rights, chat/topic context and SDK method signatures.
  A newer raw API field does not automatically become an older wrapper property.

## Maintain the pack

For a framework/API update, review the affected primary-source register, update
the pin and examples together, then repeat the relevant checks:

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_pack.py
python scripts/run_offline_checks.py
python -m unittest discover -s tests -p 'test_*.py'
```

The active [validation workflow](.github/workflows/validate.yml) also checks
JavaScript, builds the language starters and checks public endpoints. It runs
weekly on Monday at 04:17 UTC, as well as on pushes, pull requests and manual runs.
Daily source refreshes are scheduled for 04:37 UTC. Weekly Dependabot checks cover
pip, npm, Go modules, Maven, NuGet, Composer, Cargo and GitHub Actions; only eligible
minor and patch updates can auto-merge through the required `validation` check.
The daily Codex agent reviews major upgrades and instructional changes, adapts
affected examples and merges compatible changes after independent review and
successful native validation of the exact revision. Unresolved migrations remain
visible in their PRs and source-review issues.

Read the [automation guide](docs/AUTOMATION.md) for the generated-file boundary,
permissions, unresolved-change review and failure issues, and the
[agent runbook](docs/AGENT_MAINTENANCE.md) for unattended content maintenance.
The desktop agent runs at 10:30 Asia/Calcutta and needs its configured computer
awake, Codex running and working ChatGPT/GitHub sign-ins; hosted GitHub checks
continue independently. Cloning the pack does not install that local schedule.
Schedules can be delayed or disabled and credentials can stop working; the
status badge and run history show actual execution. Record actual validation,
keep entrypoints concise and update this catalog when a skill is added or
renamed. Preserve the dated source registers separately from machine observations.

## License

The repository currently has no license file. Public visibility alone does not
define reuse or redistribution permission. A maintainer can add the license they
intend; this audit does not choose one on their behalf.
