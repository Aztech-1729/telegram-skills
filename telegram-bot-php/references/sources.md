# Primary sources

Checked 2026-10-03; SDK release baseline 3.16.0 (2026-03-23).

- [Release](https://github.com/irazasyed/telegram-bot-sdk/releases/tag/v3.16.0): dated package baseline.
- [Installation](https://telegram-bot-sdk.com/docs/getting-started/installation/): Composer/PHP requirements.
- [Initialization](https://telegram-bot-sdk.com/docs/getting-started/initialize/): Api/BotsManager and Laravel setup.
- [Webhook updates](https://telegram-bot-sdk.com/docs/guides/webhook-updates/): transport and parsed-update interface; adapt old route security advice.
- [Commands](https://telegram-bot-sdk.com/docs/guides/commands-system/): modular command routing.
- [Tagged source](https://github.com/irazasyed/telegram-bot-sdk/tree/v3.16.0): API and generated request behavior lookup.
- [Longman/core](https://github.com/php-telegram-bot/core): alternative architecture boundaries, not claimed newest package coverage.

Live Telegram/hosting integration and PHP compilation are separate validation claims; see the repository validation report.

## Focused ingress/API audit: 2026-10-04

- [Tagged Update trait](https://github.com/irazasyed/telegram-bot-sdk/blob/v3.16.0/src/Methods/Update.php): getWebhookUpdate returns one UpdateObject; the older hosted guide's array prose is inaccurate.
- [Tagged HTTP trait](https://github.com/irazasyed/telegram-bot-sdk/blob/v3.16.0/src/Traits/Http.php): public post, form/multipart normalization, request and connect timeout configuration.
- The webhook guide above was reread and compared with tagged source; its token-in-route advice remains replaced by dedicated secret-header validation here.

The new pure ingress/routing tests are prepared for native PHP execution. No local PHP runtime was installed, and the official portable download failed certificate validation, so this audit did not claim a local lint/test pass. No SDK client or live webhook ran. The focused review does not advance every earlier host/framework source date.
