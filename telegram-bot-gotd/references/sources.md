# Sources and validation

**Original research cutoff and review date: 2026-10-03.** The original baseline was **github.com/gotd/td v0.162.0**, published **2026-09-18**, with a **Go 1.25.0** module directive. The focused review below records the current starter pin.

## Primary project sources

- [gotd/td source at v0.162.0](https://github.com/gotd/td/tree/v0.162.0): generated MTProto types and helper packages.
- [Client options](https://github.com/gotd/td/blob/v0.162.0/telegram/options.go): SessionStorage, UpdateHandler, Resolver and Device.
- [Bot auth](https://github.com/gotd/td/blob/v0.162.0/telegram/auth/bot.go) and [auth flow](https://github.com/gotd/td/blob/v0.162.0/telegram/auth/flow.go): Auth().Bot's authorization/error result and user flow contract.
- [Echo example](https://github.com/gotd/td/blob/v0.162.0/examples/bot-echo/main.go): dispatcher, Reply(entities, update), ordinary/channel handlers and environment helper lifecycle.
- [Manual auth example](https://github.com/gotd/td/blob/v0.162.0/examples/bot-auth-manual/main.go): explicit status-gated bot authentication.
- [Updates example](https://github.com/gotd/td/blob/v0.162.0/examples/updates/main.go): updates.New, manager.Run, authentication and outgoing-update hooks.
- [Recovery configuration](https://github.com/gotd/td/blob/v0.162.0/telegram/updates/config.go), [manager](https://github.com/gotd/td/blob/v0.162.0/telegram/updates/manager.go), and [storage interfaces](https://github.com/gotd/td/blob/v0.162.0/telegram/updates/storage.go): lifecycle, memory defaults and recovery limitations.
- [Message peer helpers](https://github.com/gotd/td/blob/v0.162.0/telegram/message/peer.go): Resolve/ResolveDomain/To/Reply signatures.
- [Session package](https://pkg.go.dev/github.com/gotd/td@v0.162.0/session): FileStorage, Storage and migration helpers.
- [Upload/download API](https://pkg.go.dev/github.com/gotd/td@v0.162.0/telegram/uploader) and [downloader](https://pkg.go.dev/github.com/gotd/td@v0.162.0/telegram/downloader): source/file-location transfers and configurable helpers.
- [Core connection pool](https://github.com/gotd/td/blob/v0.162.0/telegram/pool.go): client.Pool and CloseInvoker.
- [gotd guides](https://gotd.dev/): auth, persistence, update recovery, proxies and account guidance. Guides are moving documents; the pinned source resolves signature differences.
- [Telegram application credentials](https://core.telegram.org/api/obtaining_api_id), [Telegram API](https://core.telegram.org/api), and [MTProto](https://core.telegram.org/mtproto): authoritative protocol/account constraints.

## Alternatives reviewed

- [gotd/botapi](https://github.com/gotd/botapi): a separate Bot API-shaped layer over MTProto; not a claim of HTTP drop-in compatibility or removal of Telegram limits.
- [GoTGProto](https://github.com/celestix/gotgproto): independent wrapper conventions.
- [Archived gotg](https://github.com/pageton/gotg) points to [mtgo](https://github.com/mtgo-labs/mtgo). The old repository was archived on 2026-05-14. The successor should be evaluated through its own documentation rather than treated as import-compatible gotd.

These projects' full behavior was not compiled/integration-tested in this pack.

## Validation

The original echo asset passed **go build using Go 1.27.0 on Windows**, pinned to gotd/td v0.162.0. Dependencies/go.sum were resolved with go mod tidy. No application was executed and no Telegram authentication, session migration, proxy, upload/download or update-recovery integration test was performed.

The guide deliberately separates protocol/session recovery from application durability and avoids universal claims of API completeness, TDLib equivalence or restriction avoidance.

## Focused audit — 2026-10-04

The [official module release feed](https://proxy.golang.org/github.com/gotd/td/@latest) still reports v0.162.0. [Client.Self](https://pkg.go.dev/github.com/gotd/td@v0.162.0/telegram#Client.Self) returns the current tg.User; its Bot flag and ID identify the restored account. The starter now refuses a user/different-bot session and gates the whole update chain until verification. [Update-handler adapters](https://github.com/gotd/td/blob/v0.162.0/telegram/client.go) and [peer helpers](https://github.com/gotd/td/blob/v0.162.0/telegram/message/peer.go) establish the tested wiring. Three offline tests pass with Go 1.27.0, covering token/identity refusal, readiness and typed reply/error propagation through a fake invoker; module checksums verify. No application authentication or real recovery was performed.

## Core dependency review — 2026-10-23

The starter now pins **gotd/td v0.163.0**, published **2026-10-22**, as confirmed by the [official module feed](https://proxy.golang.org/github.com/gotd/td/@latest). The immutable tag resolves to `314d9de7c1d08f35534642de6230d8622d324399`. Its upstream Go **1.25.0** directive and dependency manifest are unchanged.

The complete module comparison accounts for all 218 changed files and the schema advance from layer **229** to **232**. Session/authentication/recovery implementations and the used client, identity, ordinary-message, dispatcher and reply interfaces remain unchanged; the echo needs no application-source migration. The generated schema includes breaking changes outside the example: custom verification descriptions use `TextWithEntities`, the Firebase PNV passkey credential constructor is removed, and StarGift withdrawal uses `tmp_password` instead of `password`. Applications using those raw APIs need a separate migration; the echo's compatibility does not establish universal source compatibility.

With **Go 1.27.3 on Windows**, all three existing offline tests, `go vet ./...`, `go build` and `go mod verify` pass at v0.163.0. Tests use a fake invoker for identity/update gating, reply routing and returned errors. No Telegram application, login, real-server recovery or transfer was run.
