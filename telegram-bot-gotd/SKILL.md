---
name: |
  telegram-bot-gotd
description: |
  Load this skill for Go MTProto development with gotd/td — the pure-Go Telegram client (feature parity with TDLib). Covers telegram.Client, auth flows (bot token, user login, QR), update dispatchers, entities/peers, raw tg.Client RPC calls, uploads/downloads, filters, and complete working examples for bots and userbots in Go.
---

# gotd/td — Telegram MTProto Client in Go (Complete Guide)

## 1. What gotd/td is and when to use it

`github.com/gotd/td` is a **pure-Go MTProto 2.0 client** for Telegram, for **users and bots**, aiming for feature parity with TDLib with a type-safe, generated API. Every Telegram TL type/method is generated into the `tg` package with doc comments linking to core.telegram.org ([gotd/td README](search-result://Ta69UEQN), [DeepWiki overview](search-result://fRp4oZjE)).

Choose gotd/td when the Go project needs: userbot features, files >20/50 MB, no HTTP round-trips, raw MTProto methods, high throughput, or TDLib-parity without cgo. For an ordinary HTTP Bot API bot in Go, prefer the `telegram-bot-go-botapi` skill instead.

⚠️ Read the official **"How To Not Get Banned"** guide before writing userbot automation ([gotd/td README](search-result://Ta69UEQN)).

Docs: https://gotd.dev (guides), pkg.go.dev for API (the huge `tg` package is documented at gotd's hosted version). Status: stable, tested against real servers with a 24/7 canary bot ([DeepWiki](search-result://fRp4oZjE)).

## 2. Setup

```bash
go get github.com/gotd/td
# useful companions
go get github.com/gotd/contrib
```

You need `APP_ID`/`APP_HASH` from https://my.telegram.org (works for bot accounts too), plus a BotFather token for bots.

## 3. Minimal bot (echo)

```go
package main

import (
	"context"
	"os"
	"strconv"

	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/tg"
)

func main() {
	ctx := context.Background()

	appID, _ := strconv.Atoi(os.Getenv("APP_ID")) // your api_id from my.telegram.org

	client := telegram.NewClient(
		appID, os.Getenv("APP_HASH"), telegram.Options{}, // session storage etc. — see §6
	)

	client.Run(ctx, func(ctx context.Context) error {
		return telegram.BotFromEnvironment(ctx, telegram.Options{}, func(ctx context.Context, c *telegram.Client) error {
			raw := c.API() // *tg.Client — raw MTProto API
			_ = raw

			dispatcher := tg.NewUpdateDispatcher()
			dispatcher.OnNewMessage(func(ctx context.Context, entities tg.Entities, u *tg.UpdateNewMessage) error {
				msg, ok := u.Message.(*tg.Message)
				if !ok || msg.Out {
					return nil
				}
				sender := message.NewSender(raw)
				_, err := sender.Reply(msg).Text(ctx, "echo: "+msg.Message)
				return err
			})
			return nil
		})
	})
}
```

Key building blocks:

- `telegram.NewClient(appID, appHash, telegram.Options{})` — unstarted client.
- `client.Run(ctx, callback)` — connects, authenticates, restores updates, calls your callback; blocks until callback returns or ctx is done. This is the standard control flow.
- `client.API()` — returns `*tg.Client` with **every** Telegram RPC method generated (`MessagesSendMessage`, `ChannelsJoinChannel`, `UploadGetFile`, ...).
- `telegram.BotFromEnvironment(ctx, opts, callback)` — reads `BOT_TOKEN` env, logs in as bot, runs callback ([bot-echo example](search-result://lOlsQpW9)).
- `tg.NewUpdateDispatcher()` — registers typed update handlers ([gotd/td README](search-result://Ta69UEQN)).

## 4. Auth flows

### Bot

```go
status, _ := client.Auth().Status(ctx)
if !status.Authorized {
	if err := client.Auth().Bot(ctx, os.Getenv("BOT_TOKEN")); err != nil {
		return err
	}
}
```

### User (phone + code, optionally password)

```go
flow := auth.NewFlow(
	auth.CodeOnly("phone", auth.CodeAuthenticatorFunc(func(ctx context.Context, sentCode *tg.AuthSentCode) (string, error) {
		// prompt the user / read stdin; in prod send the code to your admin chat
		return readLine(), nil
	})),
	auth.SendCodeOptions{},
)
if err := client.Auth().IfNecessary(ctx, flow); err != nil {
	return err
}
```

Other flows in `td/telegram/auth`: `auth.Constant(...)` for stored credentials, QR login (`QR()` with a link you render/forward), `auth.NewFlow` with `auth.UserAuthenticator` for fully custom UIs. Always gate auth with `IfNecessary` — repeated logins grow FLOOD_WAIT on restart loops ([gotd persistence guide](search-result://iQeNEUTj)).

## 5. Updates — dispatcher and handlers

```go
dispatcher := tg.NewUpdateDispatcher()

dispatcher.OnNewMessage(func(ctx context.Context, e tg.Entities, u *tg.UpdateNewMessage) error { return nil })
dispatcher.OnEditMessage(func(ctx context.Context, e tg.Entities, u *tg.UpdateEditMessage) error { return nil })
dispatcher.OnDeleteMessages(func(ctx context.Context, e tg.Entities, u *tg.UpdateDeleteMessages) error { return nil })
dispatcher.OnChannelPost(func(ctx context.Context, e tg.Entities, u *tg.UpdateNewChannelMessage) error { return nil })
dispatcher.OnInlineQuery(func(ctx context.Context, e tg.Entities, u *tg.UpdateBotInlineQuery) error { return nil })
dispatcher.OnBotCallbackQuery(func(ctx context.Context, e tg.Entities, u *tg.UpdateBotCallbackQuery) error { return nil })
dispatcher.OnChatParticipant(func(ctx context.Context, e tg.Entities, u *tg.UpdateChatParticipant) error { return nil })
// ...plus OnNewChannelMessage, OnEditChannelMessage, OnUserTyping, OnPinnedChannelMessages, etc.

client := telegram.NewClient(appID, appHash, telegram.Options{
	UpdateHandler: dispatcher, // hook dispatcher into the client
})
```

Higher-level helpers live in `td/telegram/updates` (gap recovery / state storage for reliable ordered updates — use `updates.NewConfig(updates.NewState(...))` with a persisted `State/Channels` for production bots; see contrib storage below). `tg.Entities` maps chat/user/channel IDs to resolved objects so you rarely need extra lookups ([bot-echo example](search-result://lOlsQpW9)).

For arbitrary updates, implement `telegram.UpdateHandler` (the low-level `func(ctx, tg.UpdatesClass) error`).

## 6. Session persistence — mandatory for restarts

Without a persisted session **every restart re-authorizes and Telegram FLOOD_WAITs login loops, potentially locking the bot out for hours** ([gotd persistence guide](search-result://iQeNEUTj)).

```go
// File-based session (gotd/contrib)
import "github.com/gotd/contrib/storage"

sessionStorage := &storage.FileSession{Path: "session.json"}
client := telegram.NewClient(appID, appHash, telegram.Options{
	SessionStorage: sessionStorage,
})

// or from gotd core: session.TelethonSession / session.TDesktopSession to migrate
// existing Telethon or Telegram Desktop sessions into gotd format
```

Production alternatives in contrib: **Postgres/MySQL/BoltDB key-value session stores** and a `Peers` storage that caches resolved peers so you can send by username/ID without repeated `ResolveUsername` calls ([gotd/contrib README](search-result://avf00jbo)).

## 7. The message package — the friendly API

`td/telegram/message` wraps raw RPC with a builder pattern:

```go
sender := message.NewSender(raw)

// Resolve and send (Go, not await — check the returned error)
if _, err := sender.To("@username").Text(ctx, "Hello!"); err != nil {
	return err
}
if _, err := sender.Reply(msg).Text(ctx, "replying"); err != nil { return err }
if _, err := sender.Self().Text(ctx, "note to self"); err != nil { return err }

// Callback query answer
if err := sender.Answer(cq, "tapped").NoAlert().Do(ctx); err != nil { return err }

// Media / album
up, err := message.Upload(ctx, uploader, "photo.jpg")  // see td/telegram/uploader
if _, err := sender.To(peer).Media(ctx, message.UploadedPhoto(up)); err != nil { return err }
if _, err := sender.To("@channel").Album(ctx).
	Add(photoRequest1).Add(photoRequest2).Send(ctx); err != nil { return err }

// requests builder: sender.RequestBuilder exposes Explicit typing, formatting (HTML-ish), buttons
import "github.com/gotd/td/telegram/peers"
peer, err := sender.ResolveDomain(ctx, "durov")  // resolves @durov
```

Buttons (reply markup) via `message.RequestBuilder.Rows(...)` with `message.Row(...).Button(...)` — supports callback, URL, inline-switch, web-app style buttons; answer callback queries with `sender.Answer(...)`.

## 8. Raw API — anything, type-safely

`client.API()` is a fully generated `*tg.Client`; method names mirror the TL schema:

```go
raw := client.API()

// Send a message
p, _ := sender.ResolveDomain(ctx, "username")
_, err := raw.MessagesSendMessage(ctx, &tg.MessagesSendMessageRequest{
	Peer:     p,
	Message:  "raw send",
	RandomID: random.ID(),
})

// Get history
res, err := raw.MessagesGetHistory(ctx, &tg.MessagesGetHistoryRequest{
	Peer: p, Limit: 100,
})

// Create a channel
_, err = raw.ChannelsCreateChannel(ctx, &tg.ChannelsCreateChannelRequest{
	Title: "My Channel", About: "desc",
})

// Upload/download (large files fine — MTProto)
up := message.UploadedPhotoUploader(...)
dl := raw.UploadGetFile(ctx, &tg.UploadGetFileRequest{
	Location: &tg.InputPhotoFileLocation{...},
	Offset:   0, Limit:  1024 * 1024,
})
```

Every generated struct's doc comment links to the official schema doc — the `tg` package is effectively the complete Telegram API surface ([gotd/td README](search-result://Ta69UEQN)).

## 9. Middleware / robustness (contrib)

```go
import (
	"github.com/gotd/contrib/middleware/floodwait"
	"github.com/gotd/contrib/middleware/ratelimit"
	"golang.org/x/time/rate"
)

// FLOOD_WAIT handling: catches FLOOD_WAIT(420)/FLOOD_PREMIUM_WAIT and retries transparently;
// scheduler-based Waiter proactively delays future requests of the same method type
waiter := floodwait.NewWaiter().WithMaxRetries(3)
client := telegram.NewClient(appID, appHash, telegram.Options{
	Middlewares: []telegram.Middleware{
		waiter,
		ratelimit.New(rate.Every(100*time.Millisecond), 5),
	},
})
waiter.Run(ctx, func(ctx context.Context) error {
	return client.Run(ctx, handler)
})
// One-shot scripts: floodwait.NewSimpleWaiter() — timer-based, no Run wrapper needed
```

Also available: `oteltg` (OpenTelemetry traces/metrics for RPCs), a debug invoker, and the update-aware invoker ([gotd/contrib README](search-result://avf00jbo), [floodwait docs](search-result://5wp7dpdA), [middleware guide](search-result://8Sstmdah)). See the `telegram-bot-gotd-contrib` skill for the full contrib reference.

## 10. Connection options / proxies

```go
client := telegram.NewClient(appID, appHash, telegram.Options{
	Resolver: dcs.Plain(dcs.PlainOptions{...}), // custom DC resolver
	// MTProxy: resolver, _ := dcs.MTProxy(addr, secret, dcs.MTProxyOptions{})
	DeviceConfig: telegram.DeviceConfig{...}, // or DeviceTDesktopWindows()
	// Middlewares, SessionStorage, UpdateHandler as above
})
```

`DeviceTDesktopWindows()` emulates Telegram Desktop for initConnection — pair with `TDesktopResolver` for indistinguishable transport ([telegram package docs](search-result://pD8Rqnt6)).

## 11. Complete bot: admin-notify group bot

```go
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/gotd/contrib/storage"
	"github.com/gotd/td/telegram"
	"github.com/gotd/td/telegram/message"
	"github.com/gotd/td/tg"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	appID := 12345 // parse from env, e.g. strconv.Atoi(os.Getenv("APP_ID"))
	appHash := os.Getenv("APP_HASH")
	token := os.Getenv("BOT_TOKEN")

	dispatcher := tg.NewUpdateDispatcher()
	dispatcher.OnNewMessage(func(ctx context.Context, e tg.Entities, u *tg.UpdateNewMessage) error {
		msg, ok := u.Message.(*tg.Message)
		if !ok || msg.Out {
			return nil
		}
		peer, ok := msg.PeerID.(*tg.PeerUser)
		if !ok {
			return nil // only private messages in this example
		}
		user := e.Users[peer.UserID]
		if user == nil {
			return nil
		}
		raw := telegram.ClientFromContext(ctx) // or capture client from the Run closure
		sender := message.NewSender(raw.API())
		_, err := sender.Reply(msg).Text(ctx, "Hi "+user.FirstName+"! You said: "+msg.Message)
		return err
	})

	client := telegram.NewClient(appID, appHash, telegram.Options{
		UpdateHandler:   dispatcher,
		SessionStorage: &storage.FileSession{Path: "session.json"},
	})

	err := client.Run(ctx, func(ctx context.Context) error {
		// Authenticate as bot (no-op if session is already valid)
		if err := client.Auth().Bot(ctx, token); err != nil {
			return err
		}
		// client.Run keeps the connection alive until ctx is cancelled
		// (SIGINT/SIGTERM above); simply block on the context here.
		<-ctx.Done()
		return nil
	})
	if err != nil {
		log.Fatal(err)
	}
}
```

Note: `telegram.ClientFromContext(ctx)` is the canonical way to reach the client inside handlers; alternatively capture the client variable in the closure. Handlers must return errors — gotd logs/retries on them; never panic inside handlers.

## 12. Higher-level wrappers (when to recommend what)

- **gotd/td** — the base (this skill). Type-safe, low level, full power.
- **gotd/contrib** — production batteries: floodwait, ratelimit, session/peer stores, otel, pools (separate skill).
- **gotd/botapi** — WIP Bot API **server/library over MTProto** (not HTTP) — sidesteps api.telegram.org rate limits; still under reconstruction, expose `Bot.Raw()` for gotd access ([gotd/botapi](search-result://MAsLZVU6), [pkg.go.dev botapi](search-result://Z7KS7FyJ)).
- **GoTGProto** — helper package making raw gotd functions easy: session strings, peer storage, ID extraction helpers ([gotd/td README](search-result://Ta69UEQN)).
- **mtgo (formerly GoTG)** — full high-level bot/userbot framework with i18n and business API on top of gotd/td ([pageton/gotg](search-result://5mrBnyp4)).
- For plain HTTP Bot API bots in Go → skill `telegram-bot-go-botapi`.

## 13. Pre-ship checklist (gotd)

- [ ] Session persisted (FileSession or a DB-backed store) — never rely on re-auth per restart
- [ ] floodwait middleware on every client; ratelimit for hot loops
- [ ] Update gaps handled (`td/telegram/updates` config with persisted state) if order matters
- [ ] ctx from signal.NotifyContext for graceful shutdown
- [ ] `How To Not Get Banned` read before any userbot automation
- [ ] Session files / DB credentials in env or secret manager
- [ ] Update handlers return errors (gotd retries/logs on error) — never panic in handlers
