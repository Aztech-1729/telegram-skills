---
name: |
  telegram-bot-go-botapi
description: |
  Load this skill for Go Telegram Bot API (HTTP) frameworks: go-telegram/bot (modern Bot API framework with full method coverage and handlers), go-telegram-bot-api v5 (classic low-level bindings), and PaulSonOfLars/gotgbot (PTB-inspired code-generated wrapper) — setup, handlers, middlewares, webhooks, and complete examples for each.
---

# Go Bot API Frameworks (HTTP Bot API in Go)

Three solid options; pick by project style:

| Library | Style | Choose when |
|---|---|---|
| `go-telegram/bot` | Modern framework, full Bot API methods, handlers, middlewares | Default choice for new bots |
| `go-telegram-bot-api/v5` | Thin, classic low-level bindings | You want minimal magic, no framework |
| `PaulSonOfLars/gotgbot` | PTB-inspired, code-generated, std-lib only | PTB-like ergonomics in Go |

## 1. go-telegram/bot — the modern framework

Repo: https://github.com/go-telegram/bot — Telegram Bot API framework in Go with full method coverage ([go-telegram/bot](search-result://cYTM7lFk)).

```bash
go get github.com/go-telegram/bot
```

All methods exist with the same name as the official docs but capitalized (`SendMessage`, `GetMe`, `SendPhoto`...); signatures are `(ctx context.Context, params <PARAMS>) (<response>, error)`, except `GetMe`, `Close`, `Logout` with no params. The params struct fields correspond 1:1 to Bot API parameters ([go-telegram/bot README](search-result://cYTM7lFk)).

### Minimal bot

```go
package main

import (
	"context"
	"os"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func main() {
	ctx := context.Background()
	b, err := bot.New(os.Getenv("TOKEN"))
	if err != nil {
		panic(err)
	}

	b.RegisterHandler(bot.HandlerTypeMessageText, "/start", bot.MatchTypeExact,
		func(ctx context.Context, b *bot.Bot, update *models.Update) {
			b.SendMessage(ctx, &bot.SendMessageParams{
				ChatID: update.Message.Chat.ID,
				Text:   "Hello!",
			})
		})

	b.Start(ctx) // long polling
}
```

### Handler types & match types

```go
b.RegisterHandler(bot.HandlerTypeMessageText, "hello", bot.MatchTypeExact, handler)
b.RegisterHandler(bot.HandlerTypeMessageText, "go ", bot.MatchTypePrefix, handler)
b.RegisterHandler(bot.HandlerTypeMessageText, `[0-9]+`, bot.MatchTypeRegexp, handler)
b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "vote:", bot.MatchTypePrefix, handler)

// or the universal router:
b.RegisterHandlerMatchFunc(
	func(update *models.Update) bool { return update.Message != nil && update.Message.Photo != nil },
	photoHandler,
)
```

### Sending — every Bot API method

```go
// Text
b.SendMessage(ctx, &bot.SendMessageParams{
	ChatID: chatID, Text: "<b>Hi</b>", ParseMode: models.ParseModeHTML,
})

// Photo from disk
fh, _ := os.Open("cat.jpg")
b.SendPhoto(ctx, &bot.SendPhotoParams{
	ChatID: chatID, Photo: &models.InputFileUpload{Filename: "cat.jpg", Data: fh},
	Caption: "A cat",
})

// Inline keyboard
b.SendMessage(ctx, &bot.SendMessageParams{
	ChatID: chatID, Text: "Choose:",
	ReplyMarkup: models.InlineKeyboardMarkup{InlineKeyboard: [][]models.InlineKeyboardButton{{
		{Text: "A", CallbackData: "choice:a"},
		{URL: "https://example.com", Text: "Site"},
	}}},
})

// Answer callback
b.AnswerCallbackQuery(ctx, &bot.AnswerCallbackQueryParams{CallbackQueryID: cq.ID, Text: "OK"})
```

### Middlewares

```go
b := bot.New(token, bot.WithMiddlewares(func(next bot.HandlerFunc) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		// auth / logging / throttling
		next(ctx, b, update)
	}
}))
```

Useful options: `bot.WithMiddlewares(...)`, `bot.WithUpdateHandler(...)`, `bot.WithAllowedUpdates(...)`, `bot.WithWebhookSecretToken(...)`.

### Webhook

```go
b.StartWebhook(ctx, bot.WithWebhookSecretToken(secret))
// and register:
b.SetWebhook(ctx, &bot.SetWebhookParams{
	URL: "https://example.com/hook", SecretToken: secret,
})
```

Check `repo examples` and `go-telegram/miniapp` for a Mini App example repo ([go-telegram/bot README](search-result://cYTM7lFk)).

## 2. go-telegram-bot-api v5 — classic bindings

Repo: https://github.com/go-telegram-bot-api/telegram-bot-api — site go-telegram-bot-api.dev ([v5 README](search-result://btoXJYmG)).

```go
package main

import (
	"log"
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	bot, err := tgbotapi.NewBotAPI("TOKEN")
	if err != nil {
		log.Panic(err)
	}

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60
	updates := bot.GetUpdatesChan(u) // long polling channel

	for update := range updates {
		if update.Message == nil {
			continue
		}
		msg := tgbotapi.NewMessage(update.Message.Chat.ID, update.Message.Text)
		msg.ReplyToMessageID = update.Message.MessageID
		bot.Send(msg)
	}
}
```

Webhook mode ([v5 README](search-result://btoXJYmG)):

```go
wh, _ := tgbotapi.NewWebhookWithCert("https://example.com:8443/"+bot.Token, "cert.pem")
bot.Request(wh)
updates := bot.ListenForWebhook("/" + bot.Token)
go http.ListenAndServeTLS("0.0.0.0:8443", "cert.pem", "key.pem", nil)
for update := range updates { /* ... */ }
```

Note: v5 tracks the older Bot API; verify newer methods exist before relying on them — raw requests via `bot.MakeRequest(endpoint, params)` cover any gap.

## 3. gotgbot — PTB-inspired, std-lib only

Repo: https://github.com/PaulSonOfLars/gotgbot — autogenerated from the Bot API spec: type-safe, no third-party deps, updates each processed in its own goroutine, panics recovered and logged ([gotgbot README](search-result://dshK6vAP)).

```go
package main

import (
	"log"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
)

func main() {
	b, err := gotgbot.NewBot("TOKEN", nil)
	if err != nil {
		log.Fatal(err)
	}

	updater := ext.NewUpdater(&ext.UpdaterOpts{})
	updater.Dispatcher.AddHandler(ext.NewCommand("start", func(b *gotgbot.Bot, ctx *ext.Context) error {
		_, err := ctx.EffectiveMessage.Reply(b, "Hello from gotgbot!", nil)
		return err
	}))
	// generic message handler (any non-command message)
	updater.Dispatcher.AddHandler(ext.NewMessage(ext.AnyMessage(), func(b *gotgbot.Bot, ctx *ext.Context) error {
		_, err := ctx.EffectiveMessage.Reply(b, ctx.EffectiveMessage.Text, nil)
		return err
	}))

	err = updater.StartPolling(b, &ext.StartPollingOpts{})
	if err != nil {
		log.Fatal(err)
	}
	updater.Idle() // blocks until SIGINT
}
```

Handlers: `ext.NewCommand`, `ext.NewMessage(filters, cb)`, `ext.NewCallback(pattern, cb)`, conversation support, plus webhooks via `updater.StartWebhook` with `ext.NewWebhook`. Types are 1:1 with the Bot API docs, method params structs `SendMessageOpts{}` etc.

## 4. Choosing and migrating

- New Go bot, want a framework → **go-telegram/bot**.
- Coming from python-telegram-bot habits → **gotgbot** (dispatcher/filters feel familiar).
- Minimal deps / simple scripts → **go-telegram-bot-api v5**.
- Need userbot/MTProto/large files in Go → **gotd/td** skills instead.
- gotd also has **gotd/botapi** — a WIP Bot API implementation *over MTProto* (not HTTP) that sidesteps api.telegram.org limits and exposes `Bot.Raw()` to gotd/td ([gotd/botapi](search-result://MAsLZVU6)).

## 5. Cross-cutting rules (any Go framework)

- Always `AnswerCallbackQuery` for callback taps.
- Handle 429: read `parameters.retry_after`, `time.Sleep` then retry; for go-telegram/bot errors carry `Parameters.RetryAfter`.
- Context from `signal.NotifyContext` for graceful shutdown; `updater.Idle()` in gotgbot does this for you.
- Token from env; webhook secret token verified on every request.
- Structured logging with `log/slog`; one goroutine per update is normal (gotgbot) — protect shared state with mutexes or channels.
