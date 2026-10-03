# Recipe sources

Reviewed 2026-10-03. These support API choices; the implementation and guidance
are original rather than copied upstream tutorials.

| Source | Checked subject |
|---|---|
| [PTB 22.8 JobQueue](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.jobqueue.html) | Optional job-queue dependency and async jobs |
| [PTB 22.8 Application](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.application.html) | Handler groups, lifecycle and errors |
| [Telegram Bot API](https://core.telegram.org/bots/api) | Message bounds, membership and callbacks |
| [OpenAI text generation](https://developers.openai.com/api/docs/guides/text?lang=python) | Responses API and output_text |
| [OpenAI Python Responses create](https://developers.openai.com/api/reference/python/resources/responses/methods/create) | Call parameters and storage control |
| [feedparser project](https://github.com/kurtmckee/feedparser) | Parsing fetched feed content |
| [yt-dlp options](https://github.com/yt-dlp/yt-dlp#usage-and-options) | Argument separator, config/plugins, timeout, filesize |
| [FastAPI responses](https://fastapi.tiangolo.com/advanced/custom-response/) | RedirectResponse |
| [Python SQLite](https://docs.python.org/3/library/sqlite3.html) | Transactions and explicit connection closing |

Only PTB is pinned in the base dependency file. Resolve and lock optional recipe
dependencies for the deployment; their latest release is not claimed.
No live API or downloader integration was executed during the pack audit.
