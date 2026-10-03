# Telegram Bot Skills

**13 skill guides for AI agents building Telegram bots and Mini Apps with Python or Go.**

This repository brings together Telegram fundamentals, HTTP Bot API frameworks, MTProto clients, interaction design, payments, deployment patterns, and example bot recipes. Use this README to select the right guides, then read their `SKILL.md` files before implementing a task.

**Start with [telegram-bot-fundamentals](telegram-bot-fundamentals/SKILL.md).** Every Telegram task begins there; add one framework guide and the feature guides relevant to the request.

[Agent quick start](#agent-quick-start) · [Skill catalog](#skill-catalog) · [Task bundles](#task-bundles) · [Recipes](#recipe-index) · [Installation](#installation) · [Configuration](#configuration) · [Compatibility](#compatibility-and-example-status) · [References](#official-references)

## Agent quick start

1. **Read the fundamentals in full.** Establish the account type, protocol, permissions, update delivery, and security requirements.
2. **Choose the framework.** Keep the project's existing framework when appropriate. For a new project, use the selection table below.
3. **Load only the relevant feature guides.** Use the catalog and task bundles to find exact skill names and file paths. Read each selected guide in full; loading all 13 is usually unnecessary.
4. **Check the example and current API.** Confirm the selected library supports the required methods and parameters. Resolve missing configuration, imports, application lifecycle, and business logic before using a snippet.
5. **Implement and validate the requested behavior.** Exercise the relevant update flow, authorization, persistence, and failure handling. Use the advanced-features guide when preparing deployment.

### Choose a protocol and framework

| Project requirement | Framework guide | Why it fits |
| --- | --- | --- |
| Python HTTP Bot API bot with commands, conversations, jobs, or persistence | [python-telegram-bot](telegram-bot-python-telegram-bot/SKILL.md) | Async application/handler model, `ConversationHandler`, and `JobQueue`; also the framework used by the recipes. |
| Python HTTP Bot API bot with modular routers, FSM dialogs, middleware, or dependency injection | [aiogram](telegram-bot-aiogram/SKILL.md) | Router-based structure, magic filters, typed callback data, and built-in FSM patterns. |
| Python MTProto bot or user-account client | [Telethon](telegram-bot-telethon/SKILL.md) | Account authentication, events, history, raw Telegram methods, and media transfers. |
| Go HTTP Bot API bot | [Go Bot API frameworks](telegram-bot-go-botapi/SKILL.md) | Compares `go-telegram/bot`, `telegram-bot-api/v5`, and `gotgbot/v2`. |
| Go MTProto bot or user-account client | [gotd/td](telegram-bot-gotd/SKILL.md) | Client lifecycle, authentication, typed update dispatch, generated RPCs, and transfers. |
| Operational helpers for an existing Go MTProto client | [gotd/contrib](telegram-bot-gotd-contrib/SKILL.md) | Add to gotd/td for flood-wait retries, request pacing, storage, recovery, and observability. |

**HTTP Bot API and MTProto are distinct architectures.** A normal Bot API bot needs a BotFather token. MTProto clients also need Telegram application credentials and session handling; user-account clients authenticate as that user. Choose MTProto for required account/protocol capabilities, rather than assuming every bot needs it. For large files, also evaluate the local Bot API server described in the advanced-features guide.

### Copyable agent instruction

```text
Use this repository's README as the Telegram skill index.
Read telegram-bot-fundamentals/SKILL.md in full first.
Choose the project's Python or Go framework and Bot API or MTProto architecture.
Read the selected framework SKILL.md and only the relevant feature SKILL.md files.
State the selected skill names and how they apply to the requested task.
Verify version-sensitive methods against current Telegram and framework documentation.
Treat code blocks as examples: complete configuration, authorization, persistence,
application lifecycle, and placeholders before using them.
Implement the requested behavior and report the validation actually performed.
```

## Skill catalog

The link in each row opens the actual `SKILL.md`. Its identifier matches both the directory name and YAML frontmatter `name`.

### Foundation and framework guides

| Skill identifier and file | Load when the task involves | Main coverage |
| --- | --- | --- |
| [telegram-bot-fundamentals](telegram-bot-fundamentals/SKILL.md) | **Any Telegram bot task; load first** | BotFather, tokens and application credentials, Bot API vs MTProto, updates, chat types, security, rate-limit handling, project layout, and routing to other skills. |
| [telegram-bot-python-telegram-bot](telegram-bot-python-telegram-bot/SKILL.md) | Python with `python-telegram-bot` (PTB) | Application setup, handlers and filters, callbacks, conversations, jobs, persistence, inline queries, webhooks, errors, and async performance. |
| [telegram-bot-aiogram](telegram-bot-aiogram/SKILL.md) | Python with aiogram 3 | Dispatchers and routers, `F` filters, `CallbackData`, FSM, dependency injection, middleware, media, aiohttp webhooks, scheduling, and i18n. |
| [telegram-bot-telethon](telegram-bot-telethon/SKILL.md) | Python MTProto, userbots, history, or raw Telegram operations | Bot/user authentication, sessions, event handlers, message/history operations, media transfers, raw requests, conversation patterns, and flood-wait handling. |
| [telegram-bot-go-botapi](telegram-bot-go-botapi/SKILL.md) | Go using the HTTP Bot API | Framework selection, setup, polling and webhooks, handlers, matching, middleware, messages/media, callbacks, and shared operational rules. |
| [telegram-bot-gotd](telegram-bot-gotd/SKILL.md) | Go using MTProto with `gotd/td` | Client lifecycle, bot/user authentication, update dispatch, session storage, peers, message builders, generated RPCs, uploads/downloads, and connection options. |
| [telegram-bot-gotd-contrib](telegram-bot-gotd-contrib/SKILL.md) | Reliability and operations for `gotd/td` | `floodwait`, `ratelimit`, session and peer storage, update-gap recovery, connection pools, background lifecycle, and OpenTelemetry integration. |

### Feature and implementation guides

| Skill identifier and file | Load when the task involves | Main coverage |
| --- | --- | --- |
| [telegram-bot-keyboards-ui](telegram-bot-keyboards-ui/SKILL.md) | Buttons, menus, callbacks, pagination, inline mode, or chat UX | Reply/inline keyboards, callback payloads, PTB/aiogram/raw JSON examples, pagination, formatting, custom emoji, date-time entities, reactions, and Go snippets. |
| [telegram-bot-rich-messaging](telegram-bot-rich-messaging/SKILL.md) | Catalogs, storefronts, structured reports, rich formatting, or progressive AI answers | Message entities and layouts, Rich Messages, product lists, order-flow examples, reports, native draft streaming, and manual edit patterns. |
| [telegram-bot-payments-stars](telegram-bot-payments-stars/SKILL.md) | Stars checkout, digital products, refunds, subscriptions, gifts, or provider payments | Invoice/pre-checkout/successful-payment flow, fulfillment patterns, transaction/refund guidance, subscription concepts, gifts/Premium gifting, and Mini App integration. |
| [telegram-bot-miniapps](telegram-bot-miniapps/SKILL.md) | A web interface inside Telegram | Launch modes, bot/menu setup, WebApp JavaScript APIs, theming, buttons, backend `initData` validation, a todo app sketch, and deployment considerations. |
| [telegram-bot-advanced-features](telegram-bot-advanced-features/SKILL.md) | Persistence, broadcasting, webhooks, deployment, scaling, or operational reliability | Async database patterns, state storage, batched broadcasts, retries, webhook/TLS guidance, Docker/systemd snippets, local Bot API server, logging, metrics, and testing guidance. |
| [telegram-bot-recipes](telegram-bot-recipes/SKILL.md) | A concrete bot example to adapt | Seven PTB-based designs: moderation, reminders, quiz scores, RSS publishing, AI chat, media downloading, and URL shortening. |

## Task bundles

**Read fundamentals first in every row.** The sequences below list the additional guides in a practical reading order. Where “framework” appears, use the matching guide from the selection table; feature code may need adaptation to that framework.

| User request or task | Additional guides to load |
| --- | --- |
| “Build a Python command or support bot” | [PTB](telegram-bot-python-telegram-bot/SKILL.md) or [aiogram](telegram-bot-aiogram/SKILL.md) → [keyboards-ui](telegram-bot-keyboards-ui/SKILL.md) if interactive menus are needed. |
| “Build a multi-step form or onboarding flow” | Framework → [keyboards-ui](telegram-bot-keyboards-ui/SKILL.md) → [advanced-features](telegram-bot-advanced-features/SKILL.md) for durable state. |
| “Build a Stars shop or paid-access bot” | Framework → [keyboards-ui](telegram-bot-keyboards-ui/SKILL.md) → [rich-messaging](telegram-bot-rich-messaging/SKILL.md) → [payments-stars](telegram-bot-payments-stars/SKILL.md) → [advanced-features](telegram-bot-advanced-features/SKILL.md). |
| “Build an AI chat bot with streamed replies” | Framework → [recipes](telegram-bot-recipes/SKILL.md), Recipe 5 → [rich-messaging](telegram-bot-rich-messaging/SKILL.md) for streaming and final rendering. |
| “Build a Telegram Mini App or web catalog” | Framework → [miniapps](telegram-bot-miniapps/SKILL.md) → [payments-stars](telegram-bot-payments-stars/SKILL.md) if checkout is required → [advanced-features](telegram-bot-advanced-features/SKILL.md). |
| “Build a moderation, reminder, quiz, RSS, downloader, or shortener bot” | [PTB](telegram-bot-python-telegram-bot/SKILL.md) → matching [recipe](telegram-bot-recipes/SKILL.md) → [advanced-features](telegram-bot-advanced-features/SKILL.md) for deployment. |
| “Read account history or use MTProto operations in Python” | [Telethon](telegram-bot-telethon/SKILL.md) → task-specific UI or operational guidance as needed. |
| “Build an ordinary bot in Go” | [go-botapi](telegram-bot-go-botapi/SKILL.md) → relevant feature guides; adapt Python examples to the chosen Go framework. |
| “Build a Go MTProto service with persistent sessions and retries” | [gotd](telegram-bot-gotd/SKILL.md) → [gotd-contrib](telegram-bot-gotd-contrib/SKILL.md). |
| “Deploy a bot, switch to webhooks, or fix broadcasts and rate limits” | Existing framework → [advanced-features](telegram-bot-advanced-features/SKILL.md); add [gotd-contrib](telegram-bot-gotd-contrib/SKILL.md) for Go MTProto concerns. |

## Recipe index

All seven recipes are code blocks inside [telegram-bot-recipes/SKILL.md](telegram-bot-recipes/SKILL.md), using PTB. Find the indicated section in that file, then read the framework and feature guides needed to complete it.

| Section | Example design | Setup or companion guidance |
| --- | --- | --- |
| Recipe 1 | Group moderation: SQLite warnings, threshold bans, link filtering, and welcomes | Bot administrator permissions; enforce authorization on moderation commands; PTB and advanced-features. |
| Recipe 2 | Reminders: SQLite due dates checked by a recurring job | PTB `job-queue` extra; configure timezones and retry behavior for the application. |
| Recipe 3 | Quiz: inline answers and a SQLite scoreboard | Keyboards-ui; validate callback data and control repeated answers. |
| Recipe 4 | RSS-to-channel publisher: scheduled feed checks and stored seen links | `feedparser`, PTB `job-queue`, channel posting permissions, and safe formatting. |
| Recipe 5 | AI chat: typing indicator and long-answer chunking | `openai` and `OPENAI_API_KEY`; rich-messaging supplies separate streaming patterns. |
| Recipe 6 | Media downloader: `yt-dlp` and temporary files | `yt-dlp` available to the process; avoid blocking the async handler; evaluate file-transfer limits. |
| Recipe 7 | URL shortener: generated codes stored in SQLite | Supply a domain and implement the separate HTTP redirect service. |

For a storefront, see **sections 3–4** of [rich-messaging](telegram-bot-rich-messaging/SKILL.md). For a web interface, use [miniapps](telegram-bot-miniapps/SKILL.md). These examples require application-specific authentication, data storage, and business logic.

## Installation

The repository is a collection of Markdown instructions. Each of the 13 `telegram-bot-*` directories contains one `SKILL.md` with YAML `name` and `description` frontmatter. There are no bundled executable scripts, dependency manifests, or test suites.

### Use directly from a checkout

Authenticate with a GitHub account that has access to this private repository, then clone it:

```bash
git clone https://github.com/Aztech-1729/telegram-skills.git
cd telegram-skills
```

Point your agent at `README.md`, or explicitly give it the relevant `SKILL.md` paths. This works without installing skills into a discovery directory.

### Install into an agent's skills directory

For an agent that supports directory-based `SKILL.md` discovery:

1. Find the skills directory configured by that agent.
2. Copy the complete `telegram-bot-*` folders there, preserving their names and `SKILL.md` files. Keep fundamentals alongside any selected specialized skills.
3. Refresh or restart the agent if its loader requires it, then confirm that the skills are discoverable. Automatic loading depends on the agent's own implementation.

From the repository root, a full-pack copy on macOS/Linux is:

```bash
SKILLS_DIR="/path/to/your/agent/skills"
mkdir -p "$SKILLS_DIR"
cp -R telegram-bot-* "$SKILLS_DIR/"
```

On Windows PowerShell:

```powershell
$TelegramSkillsDirectory = 'C:\path\to\your\agent\skills'
New-Item -ItemType Directory -Path $TelegramSkillsDirectory -Force | Out-Null
Get-ChildItem -Directory -Filter 'telegram-bot-*' |
    Copy-Item -Destination $TelegramSkillsDirectory -Recurse
```

Replace the destination with the actual configured directory. Before updating an existing installation, review any local edits to avoid overwriting custom instructions.

### Repository layout

```text
telegram-skills/
├── README.md
├── telegram-bot-fundamentals/SKILL.md
├── telegram-bot-python-telegram-bot/SKILL.md
├── telegram-bot-aiogram/SKILL.md
├── telegram-bot-telethon/SKILL.md
├── telegram-bot-go-botapi/SKILL.md
├── telegram-bot-gotd/SKILL.md
├── telegram-bot-gotd-contrib/SKILL.md
├── telegram-bot-keyboards-ui/SKILL.md
├── telegram-bot-rich-messaging/SKILL.md
├── telegram-bot-payments-stars/SKILL.md
├── telegram-bot-miniapps/SKILL.md
├── telegram-bot-advanced-features/SKILL.md
└── telegram-bot-recipes/SKILL.md
```

## Configuration

Reading or installing the guides requires no Telegram credentials or runtime packages. Credentials and dependencies are needed only when building the application described by a guide.

| Application area | Required configuration or dependencies |
| --- | --- |
| HTTP Bot API bot | BotFather bot token; the chosen Python package or Go module. A normal HTTP bot does not need `api_id` / `api_hash`. |
| Python MTProto / Telethon | Telegram application `api_id` and `api_hash`, bot token or user authentication, and protected session storage. |
| Go MTProto / gotd | `APP_ID`, `APP_HASH`, and `BOT_TOKEN` for bot examples; user authentication when using a user account; persisted sessions. |
| Scheduled PTB examples | The `python-telegram-bot[job-queue]` extra where `JobQueue` is used. |
| Stateful applications | The database/storage dependencies selected by the implementation; some examples use SQLite, async SQLAlchemy, or Redis patterns. |
| Webhooks | Reachable endpoint, TLS configuration where required, and webhook secret validation. |
| Mini Apps | Web frontend/backend, launch configuration, and server-side validation of Telegram `initData`. |
| Optional recipes | `feedparser` for RSS; `openai` and `OPENAI_API_KEY` for the AI example; `yt-dlp` for media downloading. |

**Token variable names differ between examples.** Fundamentals uses `TELEGRAM_BOT_TOKEN`; other guides may use `BOT_TOKEN`, `TOKEN`, or a configuration module. `TOKEN` sometimes represents a Python/Go variable that must be defined rather than an environment variable already being read. Choose one application convention and wire every example to it.

Keep bot tokens, application credentials, user sessions, webhook secrets, and provider keys outside source control. Examples that show placeholder IDs, domains, products, or secrets require your application's values.

## Compatibility and example status

The guides target **PTB 22.x, aiogram 3.x, Telethon 1.x, and Go Bot API/MTProto libraries**, and discuss Bot API 10.x features. Version labels inside individual files describe their intended context; they are not a dependency lockfile or a tested compatibility matrix. Check current framework documentation before choosing a package version or copying a signature.

**Treat the code as instructional examples to adapt.** Some sections contain abbreviated snippets, conceptual code, undefined configuration variables, or business-logic placeholders. Check syntax, imports, and library signatures as well as application logic. This repository does not include an automated test harness establishing that every example runs unchanged.

### Integration checks worth making

| Area | Check before implementation |
| --- | --- |
| Bot API naming | Use the documented wire method names such as `sendMessage`; Python SDK names such as `send_message` are a separate interface. See the [Bot API reference](https://core.telegram.org/bots/api#making-requests). |
| Button styling | The categorical “no button colors” statements in the UI/Mini App guides are outdated. Current inline and reply buttons have a `style` field; confirm SDK support. See [InlineKeyboardButton](https://core.telegram.org/bots/api#inlinekeyboardbutton) and [KeyboardButton](https://core.telegram.org/bots/api#keyboardbutton). |
| Webhook lifecycle | In PTB examples, reconcile `updater(None)` with any later `app.updater` calls. Use one supported lifecycle for the selected deployment. |
| Recipes | Define/import token configuration and invoke the entry point; enforce moderation authorization, validate callback data, and move blocking database/network/process work out of async handlers where needed. |
| Payments and storefronts | Implement durable orders, pre-checkout checks, fulfillment, access control, and duplicate-payment handling. A product called a “subscription” does not by itself implement recurring billing. |
| Mini App backend | Complete the todo example's storage and authorized API routes; replace the demonstration user-ID “session” with proper server-side authentication/session handling. |
| MTProto / Go helpers | Complete conceptual storage, update-recovery, authentication, and tracing placeholders. Verify exact package paths and lifecycle wiring; community adapters are not bundled dependencies. |
| Rich Messages and drafts | Confirm SDK support, required parameters such as `draft_id`, applicable chat types, throttling, and final-message persistence against the [Bot API reference](https://core.telegram.org/bots/api). |

When skill text and current Telegram/framework documentation disagree on an API fact, use the official reference and record the necessary adaptation. This README indexes coverage; it does not certify every code block as deployable.

## Official references

Use these canonical references for version-sensitive details. Some existing skill citations use `search-result://` links; use the sources below when those links are unavailable.

| Topic | Reference |
| --- | --- |
| Telegram Bot API, methods, fields, and recent changes | [Bot API](https://core.telegram.org/bots/api) |
| Bot creation, permissions, updates, and operational questions | [Introduction to Bots](https://core.telegram.org/bots) · [Bot FAQ](https://core.telegram.org/bots/faq) |
| Telegram application credentials and MTProto | [Obtaining api_id](https://core.telegram.org/api/obtaining_api_id) · [Telegram API](https://core.telegram.org/api) |
| Mini App launch modes, JavaScript APIs, and authentication | [Telegram Mini Apps](https://core.telegram.org/bots/webapps) |
| Stars payments for digital goods and services | [Bot Payments with Stars](https://core.telegram.org/bots/payments-stars) |
| Python frameworks | [python-telegram-bot](https://docs.python-telegram-bot.org/) · [aiogram](https://docs.aiogram.dev/) · [Telethon](https://docs.telethon.dev/) |
| Go HTTP frameworks | [go-telegram/bot](https://github.com/go-telegram/bot) · [telegram-bot-api/v5](https://github.com/go-telegram-bot-api/telegram-bot-api) · [gotgbot/v2](https://github.com/PaulSonOfLars/gotgbot) |
| Go MTProto and operational helpers | [gotd/td](https://github.com/gotd/td) · [gotd/contrib](https://github.com/gotd/contrib) |
| Local Bot API server | [telegram-bot-api](https://github.com/tdlib/telegram-bot-api) |

## Maintaining this pack

When adding or updating a skill:

- Keep its directory name and frontmatter `name` consistent; describe concrete activation triggers in `description`.
- Add its exact `SKILL.md` link to this catalog and update relevant task bundles.
- Use canonical documentation links and distinguish API facts from library-specific syntax.
- State required dependencies, credentials, persistence, permissions, and incomplete application logic.
- Describe examples and validation accurately; claim a snippet is tested only when that validation was actually performed.

## License and ownership

**Private — © Aztech-1729.** No separate `LICENSE` file is included in this repository.
