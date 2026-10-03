# gotd/contrib: operational integration reference

Checked **2026-10-03** with contrib **v0.25.0** and gotd/td **v0.162.0**. See [sources.md](sources.md) for primary sources.

## Contents

Package map; retries and limiter ordering; storage concerns; peer caches; recovery lifecycle; original starter; background client/pools; instrumentation; I/O/auth helpers; verification.

## 1. Verified package map

| Concern | Package | Integration boundary |
| --- | --- | --- |
| Scheduled retry | middleware/floodwait | telegram.Options.Middlewares plus waiter.Run |
| Request pacing | middleware/ratelimit | Token bucket over outgoing invocations |
| Session/peer/common state | bbolt, pebble, redis | Check each adapter's interfaces; they differ |
| Object/secret storage | s3, vault | Session-oriented backends with service-specific credentials |
| Peer abstractions | storage | PeerStorage, UpdateHook, ResolverCache, collection |
| Background lifecycle | bg | Connect and StopFunc around a client |
| RPC tracing/metrics | oteltg | MeterProvider and TracerProvider |
| Invoker wrappers | invoker | Debug and update-aware invocation |
| Authentication UI | auth, auth/terminal, auth/dialog | UserAuthenticator implementations |
| Partial I/O | tg_io, partio, http_io, http_range | Ranged media access and HTTP serving |
| Clock | clock | Optional clock sources, including NTP |

The current package tree includes Redis. It does not provide the former pack's postgres/MySQL constructors, storage.FileSession, pepper, or contrib/pool. Implement a documented custom session interface when a different database is required. Core gotd supplies session.FileStorage and client pools.

Import only the packages the application needs; each brings its own dependencies. Heavy stores/exporters should not be added to an echo bot by default.

## 2. Flood waits: bounded reactive retries

A scheduler-based Waiter manages delayed retries for concurrent clients. Configure it as middleware and wrap the client's run loop:

```go
waiter := floodwait.NewWaiter().
    WithMaxRetries(3).
    WithMaxWait(time.Minute)
```

Use the same waiter in Options.Middlewares and `waiter.Run(ctx, clientRunFunction)`. Both the middleware and scheduler lifetime are necessary. SimpleWaiter is timer-based and needs no Run wrapper.

The retry count and wait bound are application policy. A wait exceeding the configured bound remains an error; cancellation should stop work. FLOOD_WAIT-family handling does not automatically make a non-idempotent business operation safe to repeat.

The middleware observes method/request shapes; server limits can depend on more than that. The application still needs to surface permanent permissions/account failures and persistent throttling.

## 3. Proactive pacing and ordering

ratelimit.New takes a golang.org/x/time/rate limit and burst. For example, rate.Every(200*time.Millisecond) with burst 2 paces a small workload; it is not a documented Telegram allowance for every account or method.

Place the waiter before the limiter so its retries pass through pacing. Outgoing middleware order is significant. Decide whether telemetry should measure each attempt or the whole operation, then place it accordingly.

Avoid blocking sleeps in incoming update handlers for global broadcast pacing. Use a bounded application queue/outbox with retry state, cancellation, and per-chat scheduling when the task requires durable sends.

## 4. Separate the four stores

| Store | Contents | Why it matters |
| --- | --- | --- |
| Session | MTProto authorization and connection state | Restores account access without unnecessary login |
| Peers/access hashes | Account-scoped users/chats/channels and resolvable identifiers | Builds valid typed input peers and aids recovery |
| Updates state | pts/qts/seq/date and channel recovery position | Tracks protocol synchronization |
| Business store | Orders, entitlements, reminders, inbox/outbox | Provides the application's durable effects |

No one JSON session file implements all four. Database permissions, migrations, backup/restore, encryption and service availability remain application responsibilities.

Verified constructors include:

- `bbolt.NewSessionStorage(db, key, bucket)`
- `bbolt.NewPeerStorage(db, bucket)`
- `bbolt.NewStateStorage(db)`
- `pebble.NewSessionStorage(db, key)` and NewPeerStorage(db)
- `redis.NewSessionStorage(client, key)` and NewPeerStorage(client)

Here bbolt/pebble/redis refer to contrib packages; their driver types are different. Alias contrib bbolt and go.etcd.io/bbolt to avoid ambiguous imports. Redis uses the driver version selected by the pinned contrib module; do not casually substitute an incompatible major version.

## 5. Peer collection and resolver cache

storage.UpdateHook(nextHandler, peerStore) stores full users/chats observed in incoming updates before forwarding them. storage.NewResolverCache(nextResolver, peerStore) wraps a peer resolver; supply it to message.NewSender(...).WithResolver when needed.

These helpers avoid unnecessary re-resolution for known peers. They do not make a cache permanent, globally shared across accounts, or sufficient for a peer never observed/resolved. Account permissions and access hashes can change.

For full cache population, use the documented PeerCollector with paginated dialogs rather than manually assuming e.Users always contains every participant. Separate application display data from credential-like access-hash data.

## 6. Update recovery lifecycle

Recovery uses core `telegram/updates.New(updates.Config{...})`. Supply the manager as the client's UpdateHandler (possibly wrapped for peer collection), then invoke Manager.Run after authentication with the current account ID and correct AuthOptions.

Assign persisted StateStorage and the ChannelAccessHasher/UserAccessHasher interfaces needed for the account's workflow. A session adapter or PeerStorage does not automatically implement these update-engine interfaces.

The original starter below persists protocol state and collects peers, but leaves the manager's access-hash stores at their memory defaults. Its handled flow is ordinary/private/basic-group text; it is not a complete durable supergroup/channel recovery example. For channels, implement or select persistent hash adapters and test restoration.

Configure OnTooLong/OnChannelTooLong and newer load/access callbacks for reconciliation when required. Recovery can report gaps that the server will no longer fill. Business handlers should tolerate repeat/reordered delivery and persist their own effect identifiers.

## 7. Original bbolt starter

[assets/reliable-echo/main.go](../assets/reliable-echo/main.go) combines:

- A file-backed bbolt database closed after client/manager shutdown.
- A session store and state store.
- A peer-collecting UpdateHook.
- A typed ordinary-message echo handler.
- Waiter plus limiter, with bounded retries.
- Status-gated bot authentication and manager.Run for the client lifetime.

[The module](../assets/reliable-echo/go.mod) pins dependencies; build it using `go build .`. Its bot.db contains account authorization. Set APP_ID/APP_HASH/BOT_TOKEN and choose an appropriate working directory before deliberate execution.

This is an infrastructure starting point, not exactly-once delivery, a persisted channel hash adapter, a durable outgoing retry queue, or a business-state implementation.

## 8. Background lifecycle

For applications that cannot use a Run callback directly, use `bg.Connect(client, options...)`. Options include WithContext and WithStartupTimeout at the checked version. The returned StopFunc returns an error and waits for shutdown.

Connection readiness is not the application's authentication or business readiness. After Connect, check authentication as required. Handle connection errors before using the client and call StopFunc on successful setup; do not start client.Run concurrently on the same instance.

For scheduled floodwait middleware, keep the waiter scheduler running for the entire background-client lifetime too. Avoid a helper whose callback returns while the client remains active.

## 9. Pools belong to core gotd

Use client.Pool(max) and a generated tg client over the returned invoker when measured uploads/downloads benefit from multiple connections. Close the pool when its work ends.

Separate accounts need separate auth/session ownership. A connection pool does not select a different account, grant extra permissions, or exempt requests from flood limits.

## 10. OpenTelemetry and invokers

At the checked version, the constructor is:

```go
middleware, err := oteltg.New(meterProvider, tracerProvider)
```

Handle the error and place the returned middleware in Options.Middlewares. The earlier WithTracerProvider/WithMeterProvider options sketch was not this API.

Use real providers/exporters for useful data; no-op providers are suitable for disabled telemetry. Metrics include RPC counts, failures and duration; spans expose method/error attributes. Shut down exporters on application termination and avoid recording credentials or full message content.

invoker.NewDebug wraps a next invoker and can dump sensitive RPC payloads. Use controlled output/redaction and disable traffic dumping in ordinary production operation. invoker.UpdateHook and core updates/hook integrations serve different call sites; inspect their types before combining them.

## 11. Optional auth, I/O, and clock helpers

Terminal/dialog authenticators help interactive user login; they should not be used to invent unattended credentials. Keep codes and passwords out of normal logs.

Partial-media I/O can power an application HTTP endpoint. Add its own authentication, range/size limits and access checks rather than exposing an account's Telegram files publicly. S3/Vault require service configuration and permissions.

Clock helpers address skewed time sources. Prefer correct host time and measure the actual issue before adding an NTP dependency.

## 12. Verify the intended failure modes

Compile against the selected modules. Test handler and retry logic locally with a fake invoker. Test a chosen database adapter's session/state restore using a temporary local store without Telegram credentials.

For deployment, explicitly exercise cancellation during waits, missing/corrupt store state, disconnected databases, gap-too-long reconciliation, and bounded concurrency in an authorized environment. Documentation or compilation alone does not validate live reconnect/recovery.
