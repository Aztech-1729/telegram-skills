# Primary sources

Checked 2026-10-03. Coverage is a practical audited map, not a copy of every upstream manual.

Focused re-review **2026-10-04**: Bot API still documents **10.3 (2026-08-24)**. Rechecked update retention/subscription defaults, migration/file identifiers, HTTP Business/managed/guest routes and bot-to-bot enablement. Other lookup routes retain the prior review date; no client/server integration was executed.

| Source | Checked scope |
| --- | --- |
| [Bot API reference](https://core.telegram.org/bots/api) | HTTP envelope, current 10.3 changelog, update contexts and method/type links. |
| [Bot FAQ](https://core.telegram.org/bots/faq) | Privacy, initiated interactions, delivery and rate concerns. |
| [Bot features](https://core.telegram.org/bots/features) | Feature families and setup/routing entrypoints. |
| [Working with bots](https://core.telegram.org/api/bots) | Native client/bot identity differences. |
| [Managed bots](https://core.telegram.org/api/bots/managed-bots) | Manager/managed lifecycle. |
| [HTTP managed flow](https://core.telegram.org/bots/features#managed-bots) / [guest mode](https://core.telegram.org/api/bots/guest-mode) | HTTP manager token/access methods versus user-only native creation; separate HTTP/native guest answer paths. |
| [Connected business bots](https://core.telegram.org/api/bots/connected-business-bots) | Revocation/restart recovery, rights and native datacenter wrapping; Bot API connection types remain the HTTP implementation entrypoint. |
| [PTB Updater 22.8](https://docs.python-telegram-bot.org/en/v22.8/telegram.ext.updater.html) | Default incoming asyncio queue versus an application's durable acceptance boundary. |
| [Business](https://core.telegram.org/api/business) | Connection-based account operations. |
| [Stories](https://core.telegram.org/api/stories) | Media/publication contexts. |

SDK-specific baselines and source checks live in each framework skill. Links to niche methods are lookup routes; presence in the route map is not a claim of an included end-to-end implementation.
