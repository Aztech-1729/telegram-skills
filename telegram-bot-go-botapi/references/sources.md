# Sources and validation

**Research cutoff and review date: 2026-10-03.** Sources below are primary project/Telegram documentation. Release pins describe this pack's examples, not a guarantee of the newest version in a future environment.

## Checked versions

| Module | Example pin | Release timestamp observed | Module Go directive |
| --- | --- | --- | --- |
| github.com/go-telegram/bot | v1.27.0 | 2026-09-11 | 1.18 |
| github.com/PaulSonOfLars/gotgbot/v2 | v2.0.0-rc.36 | 2026-08-02 | 1.24 |
| github.com/go-telegram-bot-api/telegram-bot-api/v5 | v5.5.1 | 2021-12-13 | 1.16 |

The Go module service supplied these release records. The research check also inspected project source snapshots dated on or before the cutoff. gotgbot's v2 branch had changes beyond rc.36; the example compiles against the tag rather than depending on branch behavior.

## Primary references

- [go-telegram/bot README at v1.27.0](https://github.com/go-telegram/bot/blob/v1.27.0/README.md): construction, handler options and HTTP webhook integration.
- [Handlers](https://github.com/go-telegram/bot/blob/v1.27.0/handlers.go) and [options](https://github.com/go-telegram/bot/blob/v1.27.0/options.go): RegisterHandler variants, command matching, middleware/error options.
- [Error types](https://github.com/go-telegram/bot/blob/v1.27.0/errors.go): TooManyRequestsError.RetryAfter.
- [Changelog](https://github.com/go-telegram/bot/blob/v1.27.0/CHANGELOG.md): v1.27.0 transport retry/upload-buffer behavior and v1.26.0 unknown-type tolerance.
- [gotgbot rc.36 source](https://github.com/PaulSonOfLars/gotgbot/tree/v2.0.0-rc.36): updater/dispatcher boundaries, filters, conversations and samples.
- [gotgbot extension API](https://pkg.go.dev/github.com/PaulSonOfLars/gotgbot/v2@v2.0.0-rc.36/ext): PollingOpts and updater/dispatcher lifecycle.
- [Classic v5.5.1 API](https://pkg.go.dev/github.com/go-telegram-bot-api/telegram-bot-api/v5@v5.5.1): update channel, Send, StopReceivingUpdates and MakeRequest.
- [Classic project documentation](https://go-telegram-bot-api.dev/): low-level design and existing integrations.
- [Telegram Bot API](https://core.telegram.org/bots/api): wire method/field/permission definitions, callback answers, allowed updates and webhook secrets.
- [Official local Bot API server](https://github.com/tdlib/telegram-bot-api): HTTP alternative for large-file/local-server requirements.

## Scope and validation

All three original asset applications passed go build with **Go 1.27.0 on Windows** against the pins above. Their go.sum files were generated with go mod tidy. Compilation did not execute constructors or poll/send requests.

The reference's conditional integration fragments were checked against project signatures; they are not standalone applications. No real Telegram token, webhook registration, callback, media upload, or live-server test was used.

Refresh the release/API check before adding later Bot API features, and preserve the application's actual module versions when repairing an existing project.
