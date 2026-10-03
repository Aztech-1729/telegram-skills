# Sources and validation

**Research cutoff and review date: 2026-10-03.** Checked module pins: **gotd/contrib v0.25.0** (2026-07-15) and **gotd/td v0.162.0** (2026-09-18); both declare Go **1.25.0**.

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

The original reliable-echo asset passed **go build with Go 1.27.0 on Windows**, using the module pins above, bbolt v1.5.0 and golang.org/x/time v0.15.0. go mod tidy generated its dependency records.

No application was run. Real Telegram RPCs, local database runtime/restore, Redis/S3/Vault services, OpenTelemetry exporters, background-client lifecycle and floodwait timing were not integration-tested. Constructor signatures outside the asset were reviewed in the pinned sources.
