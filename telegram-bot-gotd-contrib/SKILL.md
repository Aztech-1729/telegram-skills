---
name: |
  telegram-bot-gotd-contrib
description: |
  Load this skill for production gotd/td helpers from gotd/contrib: floodwait and ratelimit middlewares, session and peer storage backends (file, Postgres, MySQL, BoltDB, Redis), client connection pools, background client runner, RPC invoker helpers, OpenTelemetry instrumentation, and reliable updates gap-recovery configuration with complete Go examples.
---

# gotd/contrib — Production Helpers for gotd/td

`github.com/gotd/contrib` holds the batteries-included helpers that would pull heavy dependencies (databases, object stores, OpenTelemetry, NTP) into the core; each package is independent so importing one only pulls what it needs ([gotd/contrib README](search-result://avf00jbo)). Guides live at gotd.dev under Helpers ([contrib packages page](search-result://fM7VF9M1)).

```bash
go get github.com/gotd/contrib
```

## 1. Middleware basics

A middleware receives the next invoker and returns a function that calls it — the classic onion pattern; they plug into `telegram.Options.Middlewares` ([middleware guide](search-result://8Sstmdah)).

```go
type Middleware interface {
	Handle(next tg.Invoker) telegram.InvokeFunc
}
client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{...},
})
```

## 2. floodwait — transparent FLOOD_WAIT retry

Telegram throttles with FLOOD_WAIT-family errors carrying "retry after N seconds":

- `FLOOD_WAIT (420)` and `FLOOD_PREMIUM_WAIT (420)` — per-method rate limits; the scheduler-based **Waiter proactively delays future requests of that type** after seeing one
- `FLOOD_SKIP_FAILED_WAIT (420)` — argument-less; retried after 1s
([floodwait docs](search-result://5wp7dpdA))

```go
waiter := floodwait.NewWaiter().WithMaxRetries(3).WithMaxWait(time.Hour)

client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{waiter},
})

// Waiter.Run keeps its scheduler running; wrap the client loop:
waiter.Run(ctx, func(ctx context.Context) error {
	return client.Run(ctx, func(ctx context.Context) error {
		// ... auth + handlers
		return nil
	})
})
```

One-shot scripts: `floodwait.NewSimpleWaiter()` — simpler timer-based variant, no Run wrapper ([middleware guide](search-result://8Sstmdah)).

## 3. ratelimit — stay under limits proactively

Token-bucket limiter (golang.org/x/time/rate) that paces outgoing requests; pairs naturally with floodwait ([gotd/contrib README](search-result://avf00jbo), [ratelimit docs](search-result://qiGuMwVt)).

```go
import "golang.org/x/time/rate"

client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{
		ratelimit.New(rate.Every(100*time.Millisecond), 5), // 10 req/s, burst 5
	},
})
```

Rule: ratelimit to avoid waits, floodwait as the safety net. Both together is the production default.

## 4. Session storage backends

Persisting the session is effectively **mandatory** — restart loops re-auth and grow FLOOD_WAIT until the bot is locked out for hours ([persistence guide](search-result://iQeNEUTj)).

```go
// File
import "github.com/gotd/contrib/storage"
client := telegram.NewClient(appID, appHash, telegram.Options{
	SessionStorage: &storage.FileSession{Path: "session.json"},
})

// Postgres (also: MySQL, BoltDB, and key-value adapters)
import "github.com/gotd/contrib/storage/postgres"
db, _ := sql.Open("pgx", dsn)
pgSession := postgres.New(db, "sessions") // table name
client := telegram.NewClient(appID, appHash, telegram.Options{
	SessionStorage: pgSession,
})

// Redis-style session storage: see gotd/session and community adapters
```

Session rows are small JSON blobs; treat the table like a secret (access controls, encryption at rest).

## 5. Peers storage — resolve once, send forever

`Peers` adapters cache resolved users/channels/channels so sending by ID doesn't require re-resolution, and give you helpers to extract chat/user IDs:

```go
import "github.com/gotd/contrib/pepper" // peer storage helpers family (check pkg.go.dev for exact pkg)
// pattern:
peersDB := ... // implements peers storage interface
dispatcher.OnNewMessage(func(ctx context.Context, e tg.Entities, u *tg.UpdateNewMessage) error {
	// e.Entities already carries resolved users/chats for the update — persist them
	for _, c := range e.Channels { /* save c.ID, c.Username, c.AccessHash */ }
	for _, u := range e.Users { /* save */ }
	return nil
})
```

The `telegram/peers` package (core) builds typed `peers.User`/`peers.Channel` objects on top of a persisted cache, supporting full peer graph queries ([gotd/contrib README](search-result://avf00jbo)).

## 6. Updates gap recovery — reliable ordered updates

MTProto delivers updates over sockets; disconnects create gaps. For bots where order/completeness matters, configure the updates engine with persisted state:

```go
import "github.com/gotd/td/telegram/updates"

// storage-backed state (contrib has SQL adapters)
state := updates.NewState(...) // persisted recovery state + channel states
client := telegram.NewClient(appID, appHash, telegram.Options{
	UpdateHandler: dispatcher,
	Updates:       updates.NewConfig(state), // enables gap recovery & fetch-for-missing
})
```

Without this, a restart may miss messages sent while the bot was down.

## 7. Client pools & background running

- **pool** (`contrib/pool`): manage multiple connections/DCs and pick the right session for the job — for multi-account or high-throughput bots.
- **background client** (contrib): `Connect` blocks until the client is connected and ready, returns a `StopFunc` to shut down — for when `client.Run`'s callback style doesn't fit your control flow; supports `WithContext` and `WithStartupTimeout` ([gotd/contrib README](search-result://avf00jbo)).

```go
stop, err := clientConnect(ctx, client) // conceptual — see contrib bg package
defer stop()
```

## 8. Invoker helpers & oteltg (observability)

```go
// invoker: debug invoker (dump RPC traffic), update-aware invoker
client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{debug.Invoke(...)},
})

// oteltg: OpenTelemetry traces + metrics for outgoing RPCs
import "github.com/gotd/contrib/oteltg"
otel := oteltg.New(oteltg.WithTracerProvider(tp), oteltg.WithMeterProvider(mp))
client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{otel},
})
```

Wire the providers to your OTLP exporter; you get per-method spans and call-count/latency histograms ([gotd/contrib README](search-result://avf00jbo)).

## 9. Reference production skeleton

```go
func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// storage
	db, _ := sql.Open("pgx", os.Getenv("DSN"))
	sessionStorage := postgres.New(db, "sessions")

	// middlewares
	waiter := floodwait.NewWaiter().WithMaxRetries(3)
	otel := oteltg.New(...)

	client := telegram.NewClient(appID, appHash, telegram.Options{
		SessionStorage: sessionStorage,
		Middlewares:     []telegram.Middleware{otel, waiter, ratelimit.New(rate.Every(time.Second/10), 10)},
		UpdateHandler:   dispatcher, // tg.NewUpdateDispatcher() with handlers
	})

	err := waiter.Run(ctx, func(ctx context.Context) error {
		return client.Run(ctx, func(ctx context.Context) error {
			if !authorized { auth flow here }
			// register handlers on dispatcher, then block:
			<-ctx.Done()
			return nil
		})
	})
	log.Fatal(err)
}
```

## 10. Checklist

- [ ] Session persisted to DB/file; restart loop tested (no re-auth on boot)
- [ ] floodwait + ratelimit middlewares on all clients
- [ ] Updates state persisted if message loss matters
- [ ] oteltg wired for production observability
- [ ] Pools only where multi-account/DC targeting is actually needed
- [ ] Signal-context shutdown; Run exits cleanly
