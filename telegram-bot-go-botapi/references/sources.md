# Sources and validation

**Original research cutoff and review date: 2026-10-03.** The focused gotgbot review below is dated **2026-10-18**; it does not advance the other libraries' review dates. Sources below are primary project/Telegram documentation. Release pins describe this pack's examples, not a guarantee of the newest version in a future environment.

## Checked versions

| Module | Example pin | Release timestamp observed | Module Go directive | Pin review |
| --- | --- | --- | --- | --- |
| github.com/go-telegram/bot | v1.27.0 | 2026-09-11 | 1.18 | 2026-10-03 |
| github.com/PaulSonOfLars/gotgbot/v2 | v2.0.0-rc.37 (prerelease) | 2026-10-17 | 1.24 | 2026-10-18 |
| github.com/go-telegram-bot-api/telegram-bot-api/v5 | v5.5.1 | 2021-12-13 | 1.16 | 2026-10-03 |

The Go module service supplied these release records. The original research check inspected project source snapshots dated on or before its cutoff and pinned gotgbot rc.36 (released 2026-08-02); the focused review below upgrades only that starter to rc.37. Compile against the selected tag rather than depending on branch behavior.

## Primary references

- [go-telegram/bot README at v1.27.0](https://github.com/go-telegram/bot/blob/v1.27.0/README.md): construction, handler options and HTTP webhook integration.
- [Handlers](https://github.com/go-telegram/bot/blob/v1.27.0/handlers.go) and [options](https://github.com/go-telegram/bot/blob/v1.27.0/options.go): RegisterHandler variants, command matching, middleware/error options.
- [Error types](https://github.com/go-telegram/bot/blob/v1.27.0/errors.go): TooManyRequestsError.RetryAfter.
- [Changelog](https://github.com/go-telegram/bot/blob/v1.27.0/CHANGELOG.md): v1.27.0 transport retry/upload-buffer behavior and v1.26.0 unknown-type tolerance.
- [gotgbot rc.36 source](https://github.com/PaulSonOfLars/gotgbot/tree/v2.0.0-rc.36): historical 2026-10-03 baseline for updater/dispatcher boundaries, filters, conversations and samples; the rc.37 review below supersedes this example pin.
- [gotgbot rc.36 extension API](https://pkg.go.dev/github.com/PaulSonOfLars/gotgbot/v2@v2.0.0-rc.36/ext): historical PollingOpts and updater/dispatcher lifecycle evidence.
- [Classic v5.5.1 API](https://pkg.go.dev/github.com/go-telegram-bot-api/telegram-bot-api/v5@v5.5.1): update channel, Send, StopReceivingUpdates and MakeRequest.
- [Classic project documentation](https://go-telegram-bot-api.dev/): low-level design and existing integrations.
- [Telegram Bot API](https://core.telegram.org/bots/api): wire method/field/permission definitions, callback answers, allowed updates and webhook secrets.
- [Official local Bot API server](https://github.com/tdlib/telegram-bot-api): HTTP alternative for large-file/local-server requirements.

## Scope and validation

All three original asset applications passed go build with **Go 1.27.0 on Windows** against their original pins (gotgbot rc.36). Their go.sum files were generated with go mod tidy. Compilation did not execute constructors or poll/send requests. The focused rc.37 result is recorded separately below.

The reference's conditional integration fragments were checked against project signatures; they are not standalone applications. No real Telegram token, webhook registration, callback, media upload, or live-server test was used.

Refresh the release/API check before adding later Bot API features, and preserve the application's actual module versions when repairing an existing project.

## Focused audit — 2026-10-04

The [classic v5.5.1 transport](https://github.com/go-telegram-bot-api/telegram-bot-api/blob/v5.5.1/bot.go) propagates HTTP URL errors and logs polling failures internally. Its starter now uses a client adapter that redacts both the credential-bearing URL and nested error message before they enter the SDK, while preserving errors.Is/As for inspection. Two additional offline tests exercise real SDK startup/polling against a fake transport; no network calls are made. Together with the modern HTTP/core/contrib checks, the repository now runs eleven Go behavior tests.

At that audit, the official Go module service's release feeds still reported the original pins: [go-telegram/bot](https://proxy.golang.org/github.com/go-telegram/bot/@latest), [gotgbot/v2](https://proxy.golang.org/github.com/!paul!son!of!lars/gotgbot/v2/@latest), and [classic v5](https://proxy.golang.org/github.com/go-telegram-bot-api/telegram-bot-api/v5/@latest).

The [pinned webhook receiver](https://github.com/go-telegram/bot/blob/v1.27.0/webhook_handler.go) reads an unbounded body, logs invalid secret/JSON and returns implicit 200, and queues accepted updates in memory. The [command matcher](https://github.com/go-telegram/bot/blob/v1.27.0/handlers.go) compares the entire command entity, including any @mention. The guide now distinguishes these limits from application HTTP validation/durability and mention parsing. Two offline tests exercise the real SDK with getMe skipped: webhook rejection/accepted dispatch/worker shutdown and bare-versus-mentioned command routing. All three assets pass go test and module checksum verification with Go 1.27.0. No Bot API requests were made.

## Focused gotgbot update — 2026-10-18

The [official release feed](https://api.github.com/repos/PaulSonOfLars/gotgbot/releases?per_page=10) marks **v2.0.0-rc.37 as a prerelease**. The Go module record reports `2026-10-17T15:13:35Z`, tag commit `0ea59f13b405f95889df3e101966a0ed1b2ebd39`, and an unchanged Go **1.24** directive. The release announces Bot API 10.3, a handler-registration concurrency fix, unknown-type handling, and rich-text rendering fixes. These are upstream release claims, not evidence of live Telegram behavior.

Compared the rc.36 and rc.37 module sources obtained through the official Go proxy and checksum database. The echo's `NewBot`, `NewDispatcher`/`DispatcherOpts`, `NewMessage(message.Text, ...)`, `Message.Reply`, `NewUpdater`, `StartPolling`/`PollingOpts`, and `Idle` call signatures remain compatible. Its application code needs no migration. `Idle` itself only blocks; graceful shutdown requires application signal handling and `Stop`.

Other rc.36 applications need a scoped migration check: `EditEphemeralMessageText` and its context variant now take `Text` or `RichMessage` in the options; `CanManageTags` changes from pointer to bool in the affected rights/member structs, and custom `GetCanManageTags` helpers are removed. Unknown discriminator variants retain raw JSON, while merged accessors can return empty values. The guide records the resulting authorization and feature-support limits.

Regenerated the starter's go.sum with `go mod tidy`. With **Go 1.27.0 on Windows**, `go mod download`, `go mod verify`, `go build -p 2 ./...`, and `go test -p 2 ./...` passed against rc.37. This starter has no test files: the result establishes checksum/build compatibility, not routing or live-delivery behavior. No constructor, polling, Bot API call, or starter binary was executed.
