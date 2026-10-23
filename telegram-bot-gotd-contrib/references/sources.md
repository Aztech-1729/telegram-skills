# Sources and validation

**Original research cutoff and review date: 2026-10-03.** Original checked module pins: **gotd/contrib v0.25.0** (2026-07-15) and **gotd/td v0.162.0** (2026-09-18); both declare Go **1.25.0**. The focused review below records the current core pin.

## Primary references

- [contrib v0.25.0 package tree](https://github.com/gotd/contrib/tree/v0.25.0): actual backend/auth/I/O package names.
- [floodwait API](https://pkg.go.dev/github.com/gotd/contrib@v0.25.0/middleware/floodwait) and [source](https://github.com/gotd/contrib/tree/v0.25.0/middleware/floodwait): scheduler/simple waiter lifecycle, retry/wait bounds and error handling.
- [ratelimit](https://github.com/gotd/contrib/blob/v0.25.0/middleware/ratelimit/ratelimit.go): token-bucket constructor and invoker integration.
- [bbolt session constructor](https://github.com/gotd/contrib/blob/v0.25.0/bbolt/session.go), [peer store](https://github.com/gotd/contrib/blob/v0.25.0/bbolt/peer_storage.go), and [update state](https://github.com/gotd/contrib/blob/v0.25.0/bbolt/state_storage.go): distinct interfaces and arguments.
- [Redis backend](https://github.com/gotd/contrib/tree/v0.25.0/redis), [Pebble](https://github.com/gotd/contrib/tree/v0.25.0/pebble), [S3](https://github.com/gotd/contrib/tree/v0.25.0/s3), and [Vault](https://github.com/gotd/contrib/tree/v0.25.0/vault): service/driver-specific stores, not interchangeable constructors.
- [Peer collection hook](https://github.com/gotd/contrib/blob/v0.25.0/storage/hook.go) and [resolver cache](https://github.com/gotd/contrib/blob/v0.25.0/storage/resolver_cache.go): persistent peer capture and resolution.
- [Background client](https://github.com/gotd/contrib/blob/v0.25.0/bg/connect.go): Connect(client, options...), WithContext, WithStartupTimeout and error-returning StopFunc.
- [OpenTelemetry constructor](https://github.com/gotd/contrib/blob/v0.25.0/oteltg/middleware.go): New(meterProvider, tracerProvider) returns middleware/error and reports RPC metrics/spans.
- [Invoker helpers](https://github.com/gotd/contrib/tree/v0.25.0/invoker): debug and update hooks.
- [Core recovery interfaces](https://github.com/gotd/td/blob/v0.162.0/telegram/updates/storage.go) and [core pool](https://github.com/gotd/td/blob/v0.162.0/telegram/pool.go): recovery hashes and connection pools belong to the core interfaces.
- [gotd middleware guide](https://gotd.dev/docs/helpers/middleware/): order of waiter and limiter.
- [bbolt project](https://github.com/etcd-io/bbolt): embedded database and ownership/lifecycle expectations.

## Scope corrections

Built-in Redis was verified. SQL databases can implement core/session interfaces, but this release does not supply the previous pack's alleged postgres/MySQL constructors. FileStorage is a core session helper; pepper and contrib/pool were not valid package paths in the checked tree.

The starter persists session and recovery state and collects peers. It leaves update-engine access-hash stores in memory, so durable channel/supergroup recovery requires additional integration. It does not implement a durable outgoing job queue.

## Validation

The reliable-echo asset passes **go test with Go 1.27.0 on Windows**, using the module pins above, bbolt v1.5.0 and golang.org/x/time **v0.16.0**. The example's resolved module directive is **Go 1.26.0**; distinguish that requirement from core/contrib's upstream Go 1.25.0 directives. Existing dependency records are preserved and module checksums verify.

No Telegram application was run. Four offline tests cover identity/update-chain gating, typed reply/error propagation, and an actual temporary bbolt session/global/channel-pts close/reopen with account separation. Real Telegram RPCs, Redis/S3/Vault services, OpenTelemetry exporters, background-client lifecycle and floodwait timing were not integration-tested. Constructor signatures outside the asset were reviewed in the pinned sources.

## Focused audit — 2026-10-04

The [contrib release feed](https://proxy.golang.org/github.com/gotd/contrib/@latest) and [core release feed](https://proxy.golang.org/github.com/gotd/td/@latest) still report v0.25.0 and v0.162.0. The [bbolt session adapter](https://github.com/gotd/contrib/blob/v0.25.0/bbolt/session.go) and [state adapter](https://github.com/gotd/contrib/blob/v0.25.0/bbolt/state_storage.go) define the separately tested interfaces. [Self's identity](https://pkg.go.dev/github.com/gotd/td@v0.162.0/telegram#Client.Self) is verified before peer collection or recovery update forwarding. The ready gate deliberately drops pre-verification updates; its local tests do not prove real startup/channel gap recovery or a durable business outbox.

## Core dependency review — 2026-10-23

The reliable starter now pins **gotd/td v0.163.0**, published **2026-10-22**, while **contrib v0.25.0**, **bbolt v1.5.0**, **x/time v0.16.0** and its resolved **Go 1.26.0** module directive remain unchanged. The [official core feed](https://proxy.golang.org/github.com/gotd/td/@latest) identifies immutable tag commit `314d9de7c1d08f35534642de6230d8622d324399`; the [contrib feed](https://proxy.golang.org/github.com/gotd/contrib/@latest) still reports v0.25.0.

The complete core module comparison preserves the session, authentication and recovery implementations and the interfaces used by the unchanged contrib adapters. Layer **229** advances to **232** without requiring application-source edits in the reliable echo. See the [core migration review](../../telegram-bot-gotd/references/sources.md) for generated raw-API changes outside these examples; this review establishes compatibility for the bundled wiring, not all possible contrib applications or live recovery behavior.

With **Go 1.27.3 on Windows**, all four existing offline tests, `go vet ./...`, `go build` and `go mod verify` pass with the new core pin. The temporary bbolt close/reopen test exercises session/global/channel-pts persistence and account separation; the other fixtures use a fake invoker. No Telegram application, authentication, live gap recovery, floodwait timing or external storage/exporter service was exercised.
