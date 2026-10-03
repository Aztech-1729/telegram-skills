# 🤖 Telegram Bot Skills Pack

> **Professional AI-agent skill kit for building Telegram bots of any kind** — 13 deeply detailed, production-grade skills, current as of **October 2026** (Bot API 10.1–10.3).

Current with: **Bot API 10.1–10.3** · **python-telegram-bot v22.8** · **aiogram 3.30** · **Telethon 1.45** · **gotd/td + gotd/contrib (Go)**

---

## 📚 Skills Overview

| # | Skill | Purpose |
|---|-------|---------|
| 1 | `telegram-bot-fundamentals` | **Entry point & routing hub** — BotFather, tokens, Bot API 10.x fundamentals, security rules, Bot API vs MTProto decision guide |
| 2 | `telegram-bot-python-telegram-bot` | PTB v22 — handlers, filters, JobQueue, persistence, webhooks, ConversationHandler, async performance |
| 3 | `telegram-bot-aiogram` | aiogram 3 — routers, magic filters (F), FSM, dependency injection, middlewares, i18n |
| 4 | `telegram-bot-telethon` | MTProto userbots & bot accounts — events, 2 GB files, raw API calls, FloodWait safety |
| 5 | `telegram-bot-keyboards-ui` | Every button type (callback, URL, web_app, switch_inline, pay, copy_text), premium emoji, tg-time, pagination, color truth |
| 6 | `telegram-bot-rich-messaging` | Rich Messages (`sendRichMessage`/Blocks), Rich HTML, streaming drafts (`sendMessageDraft`), premium shop storefront layout |
| 7 | `telegram-bot-payments-stars` | Telegram Stars — invoices, refunds, gifting Premium, subscriptions, revenue withdrawal, initData HMAC validation |
| 8 | `telegram-bot-advanced-features` | Production engineering — DB-backed state, broadcasts, webhooks (Docker/nginx/TLS), local Bot API server, rate-limit strategy, structured logging, testing |
| 9 | `telegram-bot-miniapps` | Mini Apps — BotFather setup, web_app buttons, Telegram WebApp JS API, backend validation, theming, full working example |
| 10 | `telegram-bot-recipes` | 7 complete runnable bots: admin/moderation, reminders, quiz with scores, RSS publisher, AI chat with streaming, file downloader, URL shortener |
| 11 | `telegram-bot-go-botapi` | Go HTTP frameworks — go-telegram/bot, telegram-bot-api v5, gotgbot: handlers, middlewares, webhooks |
| 12 | `telegram-bot-gotd` | Go MTProto — telegram.Client, auth flows (bot token/user/QR), update dispatchers, raw tg.Client RPC, uploads/downloads |
| 13 | `telegram-bot-gotd-contrib` | Go production — floodwait/ratelimit middlewares, session & peer storage backends, connection pools, background runner, OpenTelemetry |

## 🚀 Install

Copy each skill folder into your agent's skills directory:

```
<skills-root>/telegram-bot-fundamentals/SKILL.md
<skills-root>/telegram-bot-python-telegram-bot/SKILL.md
...
```

Each folder contains a single `SKILL.md` with YAML frontmatter (name + description) followed by the full skill content.

## 🧭 Routing

**Always load `telegram-bot-fundamentals` FIRST** for any Telegram bot task — it contains the routing table that directs the agent to the correct specialized skill:

- **Python + Bot API** → `python-telegram-bot` or `aiogram`
- **Python + MTProto** (userbots, 2 GB files) → `telethon`
- **Go** → `go-botapi` (HTTP) or `gotd` (MTProto) + `gotd-contrib` (production helpers)
- **UI/buttons/keyboards** → `keyboards-ui`
- **Rich formatting / storefronts / streaming** → `rich-messaging`
- **Payments / Stars / monetization** → `payments-stars`
- **Web Apps** → `miniapps`
- **Deployment / scale / webhooks / Docker** → `advanced-features`
- **Need a ready-made starting point** → `recipes`

## ✨ Highlights

- ✅ **Complete coverage**: from "hello world" to production deployment with Docker, TLS webhooks, and local Bot API servers
- ✅ **Honest documentation**: e.g. the Bot API has **no button color parameter** — the pack documents the emoji-prefix trick and that real colors exist only in Mini Apps
- ✅ **Oct 2026 features**: `sendRichMessage`, Rich Blocks (Slideshow/Collage), rich buttons (10.3), message drafts, ephemeral messages, Communities, Channel DMs, Threaded mode, paid broadcast (0.1 Stars/msg, 10,000 Stars minimum)
- ✅ **Validated code**: every example checked for handler ordering, undefined references, async correctness, and placeholder bugs
- ✅ **7 fully runnable bots** in the recipes skill — copy, set your token, and run

## 📄 License

Private — © Aztech-1729
