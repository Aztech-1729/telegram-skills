# Upstream source status

Last attempted check: **2026-10-04T05:06:32Z**.

266 sources: 233 unchanged, 1 changed this run, 32 newly observed, 0 unavailable.

This generated report checks the official source ledgers and configured release feeds. A successful fetch establishes an observed content hash. It does **not** certify that a person or agent reviewed the content, that the guides support the new release, or that examples were tested against it.

The original editorial audit is recorded separately in each skill's `references/sources.md`. Machine checks never advance those dates or change instructions. A pending change remains visible after subsequent unchanged checks until its state is explicitly reviewed in a content update.

## Changes requiring content review

| Official source | Affected skills | First detected |
| --- | --- | --- |
| [https://crates.io/api/v1/crates/teloxide/0.17.0](https://crates.io/api/v1/crates/teloxide/0.17.0) | rust | 2026-10-03T21:18:41Z |
| [https://www.nuget.org/packages/Telegram.Bot/22.10.3.2](https://www.nuget.org/packages/Telegram.Bot/22.10.3.2) | dotnet | 2026-10-03T16:17:01Z |

## Unavailable sources

Failures keep the last successful hash and check date; they never become accepted content.

| Source | Failure | Retry classification |
| --- | --- | --- |
| None | — | — |

## Observed release feeds

Versions below are upstream observations, not upgraded or certified example dependencies.

| Feed | Observed versions (gotgbot includes release candidates) | Last successful check |
| --- | --- | --- |
| [https://api.github.com/repos/PaulSonOfLars/gotgbot/releases?per_page=10](https://api.github.com/repos/PaulSonOfLars/gotgbot/releases?per_page=10) | v2.0.0-rc.36, v2.0.0-rc.35, v2.0.0-rc.34, v2.0.0-rc.33, v2.0.0-rc.32 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/go-telegram/bot/releases?per_page=10](https://api.github.com/repos/go-telegram/bot/releases?per_page=10) | v1.27.0, v1.26.0, v1.25.0, v1.24.0, v1.23.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/gotd/contrib/releases?per_page=10](https://api.github.com/repos/gotd/contrib/releases?per_page=10) | v0.25.0, v0.24.0, v0.23.0, v0.22.0, v0.21.1 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/gotd/td/releases?per_page=10](https://api.github.com/repos/gotd/td/releases?per_page=10) | v0.162.0, v0.161.0, v0.160.0, v0.159.0, v0.158.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/irazasyed/telegram-bot-sdk/releases?per_page=10](https://api.github.com/repos/irazasyed/telegram-bot-sdk/releases?per_page=10) | v3.16.0, v3.15.0, v3.14.0, v3.13.0, v3.12.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/pengrad/java-telegram-bot-api/releases?per_page=10](https://api.github.com/repos/pengrad/java-telegram-bot-api/releases?per_page=10) | 10.3.0, 10.1.0, 10.0.0, 9.6.0, 9.5.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/php-telegram-bot/core/releases?per_page=10](https://api.github.com/repos/php-telegram-bot/core/releases?per_page=10) | 0.83.1, 0.83.0, 0.82.0, 0.81.0, 0.80.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/rubenlagus/TelegramBots/releases?per_page=10](https://api.github.com/repos/rubenlagus/TelegramBots/releases?per_page=10) | v10.3.0, v10.2.1, v10.2.0, v10.1.1, v10.1.0 | 2026-10-04T05:06:32Z |
| [https://api.github.com/repos/teloxide/teloxide/releases?per_page=10](https://api.github.com/repos/teloxide/teloxide/releases?per_page=10) | v0.17.0, v0.16.0, v0.15.0, v0.14.1, v0.14.0 | 2026-10-04T05:06:32Z |
| [https://api.nuget.org/v3-flatcontainer/telegram.bot/index.json](https://api.nuget.org/v3-flatcontainer/telegram.bot/index.json) | 22.10.3.2, 22.10.3.1, 22.10.3, 22.10.2.1, 22.10.2 | 2026-10-04T05:06:32Z |
| [https://crates.io/api/v1/crates/teloxide](https://crates.io/api/v1/crates/teloxide) | 0.17.0 | 2026-10-04T05:06:32Z |
| [https://pypi.org/pypi/Telethon/json](https://pypi.org/pypi/Telethon/json) | 1.45.0 | 2026-10-04T05:06:32Z |
| [https://pypi.org/pypi/aiogram/json](https://pypi.org/pypi/aiogram/json) | 3.31.0 | 2026-10-04T05:06:32Z |
| [https://pypi.org/pypi/python-telegram-bot/json](https://pypi.org/pypi/python-telegram-bot/json) | 22.8 | 2026-10-04T05:06:32Z |
| [https://registry.npmjs.org/grammy/latest](https://registry.npmjs.org/grammy/latest) | 1.46.0 | 2026-10-04T05:06:32Z |
| [https://registry.npmjs.org/skills/latest](https://registry.npmjs.org/skills/latest) | 1.7.0 | 2026-10-04T05:06:32Z |
| [https://registry.npmjs.org/telegraf/latest](https://registry.npmjs.org/telegraf/latest) | 4.16.3 | 2026-10-04T05:06:32Z |
| [https://repo.packagist.org/p2/irazasyed/telegram-bot-sdk.json](https://repo.packagist.org/p2/irazasyed/telegram-bot-sdk.json) | v3.16.0, v3.15.0, v3.14.0, v3.13.0, v3.12.0 | 2026-10-04T05:06:32Z |

## Coverage and operation

- Every HTTPS link in `telegram-bot-*/references/sources.md` is harvested and deduplicated without its fragment.
- `automation/sources.json` adds current documentation and stable-release feeds; it also restricts destinations and redirects.
- HTML navigation is discarded; JSON release feeds retain semantic release fields. Website layout changes may still require triage.
- Requests have time and size limits, bounded retries and per-host concurrency. Private endpoints and credentials are not used.
- Run `python scripts/check_upstream.py --write --report-json upstream-report.json` to refresh generated evidence.
- Run with `--strict` to fail on any unavailable source. The default exits successfully for recorded upstream failures so evidence can be published.
- `automation/upstream-state.json` preserves successful observation dates, hashes and unresolved changes. After updating and testing affected guides, explicitly set `reviewed_sha256` to the current hash, set `editorial_reviewed_at`, and remove `pending_change_since` for reviewed entries.
