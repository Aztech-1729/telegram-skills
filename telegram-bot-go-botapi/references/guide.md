# Go HTTP frameworks: implementation reference

Checked on **2026-10-03**. Read [sources.md](sources.md) for pinned versions and source scope.

## Contents

Selection and installation; starter applications; handlers and middleware; messages/media/callbacks; webhooks; failures and concurrency; migration and verification.

## 1. Select the library

| Library | Appropriate fit | Compatibility decision |
| --- | --- | --- |
| go-telegram/bot | A framework with context-aware requests, matching, and middleware | Starter pins v1.27.0; examine its generated models for the exact feature. |
| gotgbot/v2 | Updater/dispatcher structure, filters, handler groups, conversations | Starter pins v2.0.0-rc.36; this is a release candidate. Do not equate the current branch with that tag. |
| go-telegram-bot-api/v5 | Existing thin-binding applications with explicit routing | Starter pins v5.5.1, a 2021 release. New Bot API fields can be absent. |
| gotd/td | User accounts or an MTProto-specific requirement | Separate protocol and credential/session workflow; use the gotd skill. |

Both modern HTTP alternatives generate or maintain typed Bot API surfaces. Generation does not prove parity with a server version released later. For large files, assess the official local Bot API server before changing protocols.

In an application module, install only the selected library:

```bash
go get github.com/go-telegram/bot@v1.27.0
# Alternative:
go get github.com/PaulSonOfLars/gotgbot/v2@v2.0.0-rc.36
# Existing classic integration:
go get github.com/go-telegram-bot-api/telegram-bot-api/v5@v5.5.1
```

Keep go.mod and go.sum in application source control. The module directives at these pins are Go 1.18, 1.24, and 1.16 respectively; use a supported Go toolchain that meets all selected dependencies.

## 2. Original starter applications

- [go-telegram/bot echo](../assets/go-telegram-echo/main.go) with [go.mod](../assets/go-telegram-echo/go.mod): custom update predicate, checked send errors, and signal context.
- [gotgbot echo](../assets/gotgbot-echo/main.go) with [go.mod](../assets/gotgbot-echo/go.mod): imported handlers/filter packages, bounded dispatcher concurrency, error hook, and updater lifecycle.
- [classic v5 echo](../assets/classic-echo/main.go) with [go.mod](../assets/classic-echo/go.mod): explicit update-channel loop and shutdown.

Copy one complete asset directory into the application's chosen location. From that directory, `go build .` checks compilation. Set TELEGRAM_BOT_TOKEN before deliberately starting it with `go run .`. Constructors may call getMe; running is a live Telegram operation.

These starters echo text only. They do not implement a shop, durable workflow, callback authorization, queued retries, or deployment.

## 3. go-telegram/bot: handler and middleware wiring

A handler receives `context.Context`, `*bot.Bot`, and `*models.Update`. The update's message/callback fields are optional. Check the variant before dereferencing.

Use `RegisterHandler` for text or callback-data matching and `RegisterHandlerMatchFunc` for arbitrary predicates. Entity-based command matching accepts arguments after the command, but at v1.27.0 **does not strip an @botname mention**:

```go
b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, startHandler)
b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "page:", bot.MatchTypePrefix, pageHandler)
```

These registration fragments assume existing handler functions with the declared signature. For `/start@YourBot`, explicitly register `start@YourBot` or implement a command-entity parser that validates the mention against the current bot. Do not accept another bot's addressed command. Telegram entity offsets/lengths are UTF-16 units; a general parser cannot blindly slice Go UTF-8 bytes. Exact, prefix, contains, command, and regexp matching have distinct semantics; inspect the chosen tag's handler implementation before relying on match order.

Use `WithDefaultHandler` for a fallback, `WithAllowedUpdates` for receiver filtering, and `WithErrorsHandler` for framework errors. `WithMiddlewares` accepts wrappers around HandlerFunc. Handle both returns from `bot.New`:

```go
b, err := bot.New(token, bot.WithMiddlewares(func(next bot.HandlerFunc) bot.HandlerFunc {
    return func(ctx context.Context, b *bot.Bot, u *models.Update) {
        next(ctx, b, u)
    }
}))
if err != nil {
    return err
}
```

This is an integration fragment; insert authorization/logging at the wrapper's boundary rather than trusting an update's payload. Middleware for incoming updates is different from retries for outgoing requests.

## 4. Requests, media, and keyboards

go-telegram/bot requests use structs such as `bot.SendMessageParams`. Required positional data lives in those structs; many methods return a typed value plus error. Do not assume every method has an identical signature.

Files can use `models.InputFileString` for a URL/file_id or `models.InputFileUpload` with a filename and reader. Open the file with checked errors and keep it open until SendPhoto/SendDocument returns; then close it. At v1.27.0 uploads are buffered to support HTTP transport retries, so account for memory when sending large files.

Use `models.InlineKeyboardMarkup` and `models.InlineKeyboardButton` for callback/URL buttons. Acknowledge callbacks with AnswerCallbackQuery even when replacing a menu. Validate callback ownership and server-side state before any mutation. Use the keyboards guide for payload size and chat restrictions.

For formatting, either send plain text or escape untrusted values in the selected parse mode. New style, draft, Rich Message, business, or payment fields must be checked against the pinned models and official Bot API.

## 5. gotgbot: distinct package boundaries

The base package owns request methods and models. Extension packages provide dispatch:

- `ext.NewDispatcher(&ext.DispatcherOpts{...})` configures errors, handler groups and MaxRoutines.
- `ext.NewUpdater(dispatcher, opts)` uses that dispatcher.
- `handlers.NewCommand`, `handlers.NewMessage`, and `handlers.NewCallback` live under `ext/handlers`.
- Message/callback filters live under `ext/handlers/filters`, including the message.Text predicate used by the asset.
- `updater.StartPolling(b, &ext.PollingOpts{})` starts reception; Idle keeps the program alive and handles shutdown.

An ext.Context provides EffectiveMessage/EffectiveChat for applicable updates. It does not guarantee every update has a message. Handler return errors go to the configured dispatcher error hook. Conversations and handler groups are SDK facilities; persistent business state still needs an application store.

Request methods generally take required positional arguments and an options pointer, rather than a context plus Params struct. For deadlines use RequestOpts supported by the chosen method. Refer to the official webhook and conversation samples for the pinned release rather than inventing ext constructors.

## 6. Classic v5: explicit control

Use NewBotAPI, NewUpdate/GetUpdatesChan, and NewMessage/Send. Route updates yourself, including edited messages, callbacks, inline queries, and service messages.

Newer API fields absent from v5 require a compatibility decision: migrate the application, or isolate raw MakeRequest calls and manually model their responses. Raw calls do not add SDK unmarshalling support for new incoming variants.

The classic README's webhook example embeds the token in the URL. Prefer a separate unpredictable route and validate Telegram's webhook secret header in the application's HTTP handler. If the pinned WebhookConfig lacks a required field, setWebhook can be sent using a carefully scoped raw request.

## 7. Webhooks: receiver plus HTTP server

For go-telegram/bot, configure `WithWebhookSecretToken(secret)` at construction. Supply the same secret in SetWebhookParams. Run `go b.StartWebhook(ctx)` and mount a validated HTTP adapter around `b.WebhookHandler()` on the intended route.

At **v1.27.0**, the native handler logs wrong/missing configured secrets and malformed JSON, then returns without writing a response: HTTP servers ordinarily return **200**. It reads the whole request body and enqueues accepted updates in process memory. Add method/header validation with explicit 4xx responses, a body limit (`http.MaxBytesReader` or an equivalent proxy/application boundary), and request deadlines before delegation. Reject invalid JSON without recording its raw body. If accepted work must survive a crash, persist the update/inbox before acknowledging and dispatch it from an application worker; the native queue alone cannot establish that contract. [Pinned receiver source](https://github.com/go-telegram/bot/blob/v1.27.0/webhook_handler.go).

StartWebhook accepts the context; it does not itself listen on a port. The application must provide:

1. A reachable public webhook URL and matching routing.
2. TLS at the application or reverse proxy as required by the Bot API.
3. Header verification, request size/time limits, and health/error reporting.
4. Coordinated shutdown of the HTTP server and bot worker context.
5. A deployment plan for setWebhook/deleteWebhook and pending updates.

Avoid starting polling for the same token. Do not delete pending updates automatically during an ordinary restart; select that behavior only when discarding them is intentional.

For gotgbot use the chosen release's WebhookOpts and upstream webhook sample. Classic v5 can decode webhook updates with its HTTP helpers, but route/security and new setWebhook fields remain application responsibilities.

## 8. Failures, pacing, and state

At go-telegram/bot v1.27.0, rate-limit errors expose `*bot.TooManyRequestsError.RetryAfter`; the old pack's Parameters.RetryAfter access was incorrect for this SDK. Use errors.As, honor retry delay, and make waits context-cancellable. Do not busy-loop on 429.

Separate retryable throttling/transient failures from authorization, permission and bad-parameter failures. Bound attempts and total wait. If a send response is lost, resending can produce a duplicate; an application outbox/deduplication policy is preferable to an unbounded retry wrapper.

Framework workers and goroutines do not serialize shared state for you. Protect in-memory maps, scope dialogue state by chat/user as needed, and persist orders/reminders outside the handler. Use a bounded queue for broadcasts rather than starting one goroutine per recipient.

## 9. Migration and checks

Preserve update semantics, filters, callback routes, deadlines, parse modes, file reuse, and error propagation when changing libraries. Recheck account permissions and BotFather privacy settings rather than assuming a library migration fixes them.

For offline verification: build the selected asset/application, use captured Update fixtures for routing, and fake the outgoing client for sends and callback answers. For webhook verification: test malformed JSON, incorrect/missing secret, and shutdown locally. A build alone does not validate live delivery or Telegram's permissions.

[The go-telegram offline tests](../assets/go-telegram-echo/main_test.go), run with `go test ./...` in that asset directory, exercise the actual pinned SDK's command-mention and webhook rejection/dispatch/worker-stop behavior. They deliberately skip getMe and never poll or send. The tests document the receiver's implicit-200 limit; they do not certify an application's outer HTTP adapter.

## 10. Diagnose the boundary that failed

| Symptom | Inspect first | Repair at the right layer |
| --- | --- | --- |
| Private commands work, group commands do not | BotFather privacy, addressed command entities, allowed updates, handler order | Test the selected SDK with a mention fixture; keep actor/bot authorization distinct |
| Webhook URL is 200 but no handler runs | Secret, decoding/error hook, mounted route and running workers | Verify the SDK's actual status behavior and application acknowledgment policy |
| Duplicates appear after restart | Poll offset/queue lifetime, overlapping receivers and effect records | Receiver progress is separate from a committed business effect; use a durable inbox/idempotency key where needed |
| State races despite a worker count | Handler goroutines, state key, map/DB synchronization | Bound receiver work and serialize each stateful flow explicitly |
| Send hangs or returns permission/429 errors | Method deadline, bot/chat rights and typed error | Use per-operation cancellation, retry only eligible failures, and show an accurate outcome |

For menus, use the selected SDK's callback answer method before slow work, then look up trusted state and replace the relevant message. An expired payload needs a short recovery action, such as reopening the menu; successful acknowledgment is not successful fulfillment. Put text describing the current choice beside buttons, retain a `/cancel` or command alternative for forms, and avoid success copy before a durable operation commits. Read [bot UX](../../telegram-bot-ux/SKILL.md) for dialogue/navigation, [accessibility](../../telegram-bot-accessibility/SKILL.md) for nonvisual/localized operation, and [Mini App design](../../telegram-bot-miniapp-design/SKILL.md) plus [Mini App security](../../telegram-bot-miniapps/SKILL.md) when the requested interface includes the web client.
