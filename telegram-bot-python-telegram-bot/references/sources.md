# PTB source register

Checked **2026-10-03**. Baseline: **PTB 22.8**, released **2026-06-12**, Python **3.10+**, native **Bot API 10.0**. Telegram API **10.3** was announced **2026-08-24**. No sources after the cutoff were used. Versioned docs fix the framework scope; live Telegram/wiki/package pages must be rechecked for future work.

| Canonical primary source | Verified scope |
| --- | --- |
| https://docs.python-telegram-bot.org/en/v22.8/ | Python 3.10+, API 10.0 coverage, install and optional extras |
| https://docs.python-telegram-bot.org/en/v22.8/changelog.html | 22.8 release 2026-06-12, API additions and keyword-argument migrations |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.application.html | Handler groups, polling/webhook lifecycle and runner hooks |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.applicationbuilder.html | Updater None, concurrency warning and pool configuration |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.filters.html | Valid namespaces, custom/composite filters |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.callbackcontext.html | Per-user/chat/bot dictionaries, jobs and errors |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.callbackqueryhandler.html | Pattern types, regex matching and arbitrary callback data |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.callbackquery.html | Answer/edit shortcuts and inaccessible/inline messages |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.conversationhandler.html | Sequential processing, keys, timeout and named persistence opt-in |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.picklepersistence.html | Trusted-file data storage and update interval |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.basepersistence.html | Custom backend interface and copied data |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.jobqueue.html | Seconds, callbacks, timezones and repeating job immediacy |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.inputfile.html | Accepted inputs and file-handle lifetime |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.file.html | Download methods |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.helpers.html | Escaping and deep-link utilities |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.updater.html | Built-in receiver and secret argument |
| https://docs.python-telegram-bot.org/en/v22.8/examples.customwebhookbot.html | Custom receiver and explicit queue/lifecycle |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.inlinequery.html | Current answer arguments and pagination |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.bot.html | Message/media/admin/command APIs |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.error.html | Exception classes |
| https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.aioratelimiter.html | Bounded RetryAfter retries/default zero |
| https://pypi.org/pypi/python-telegram-bot/22.8/json | Package metadata/upload date and installable release |
| https://github.com/python-telegram-bot/python-telegram-bot/wiki/Bot-API-Forward-Compatibility | Official approach for unwrapped fields/methods; scope limitations |
| https://core.telegram.org/bots/api | Dated API 10.3 notice; delivery, callback and file constraints |
| https://core.telegram.org/bots/features#deep-linking | Start payload/launch semantics |

The starter is original code. Offline checks do not validate Telegram credentials, delivery, permission grants, webhook hosting or throughput. See [validation record](validation.md).

## Focused audit — 2026-10-04

The [official release feed](https://pypi.org/pypi/python-telegram-bot/json) still reports 22.8. The [ConversationHandler contract](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.conversationhandler.html) and installed 22.8 implementation confirm state is applied after the awaited callback returns. The completion handler now retains data across reply failure; actual handler/filter checks also cover nontext input and specific-before-recovery callback routing. Eight offline tests passed in an isolated Python 3.12 environment. The native Bot API 10.0 versus server 10.3 boundary remains unchanged.
