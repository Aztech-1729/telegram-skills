# C#/.NET implementation guide

## Baseline and migration

Use the NuGet feed as the package release source, then inspect the matching tag/API. The checked package is 22.10.3.2 (2026-09-25). It targets .NET 6/.NET Standard 2.0; the example project chooses net8.0 deliberately. Modern API calls use names such as `GetMe` and `SendMessage`; older tutorials use `...Async` suffixes and older types. Do not combine those APIs blindly. See [NuGet package](https://www.nuget.org/packages/Telegram.Bot/22.10.3.2) and the [quickstart](https://telegrambots.github.io/book/1/quickstart.html).

## Receiving and dispatch

Event subscriptions start reception in the tagged client. `OnMessage` receives several message-like updates; explicitly filter the update type if an operation must run only once for an original message. When OnMessage is subscribed, those updates are handled there rather than also passed to OnUpdate. Route remaining update kinds through a single dispatcher. Install the error boundary before starting reception. See [tagged client](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/TelegramBotClient.cs).

Alternatively, use the documented polling/receiver API when custom cancellation, allowed updates or hosting are required. An ASP.NET Core app should receive webhooks and dispatch Update objects through its own service. Do not subscribe polling events in a webhook application. Use a hosted-service stop token for long-running workers; Console.ReadLine is suitable only for an interactive console example.

## ASP.NET Core webhooks

Configure the bot client through DI and request-scoped application dependencies. Register the webhook using the selected version's API; validate the dedicated secret header before parsing/processing. Ensure JSON serialization uses the package's supported options/types for Telegram payloads. Preserve bot/update identity across accepted work, bound body size, and offload slow operations to durable workers when needed. Return a retryable failure when work could not be accepted; acknowledgment does not prove fulfillment.

Use a specific endpoint exemption only where framework antiforgery middleware would otherwise reject Telegram requests; do not disable application-wide protections. The webhook secret does not authorize application commands or buyer access. Match reverse-proxy/TLS/URL configuration to the deployed endpoint. Check official [examples](https://github.com/TelegramBots/Telegram.Bot.Examples) for the current host integration before adapting it.

## Messages, callbacks and files

Use strongly typed request/markup objects from the chosen package. Answer callback queries promptly; validate resource ownership and actor/bot rights before subsequent work. Inline mode and payments require different update routing. Escape dynamic HTML or send plain text. Use proper file input/stream types, dispose opened streams, and check individual upload/download constraints. Add user/chat/topic/business identifiers to state keys where the feature requires them.

The starter's Echo.BuildReply constructs a SendMessageRequest with forum MessageThreadId and DirectMessagesTopicId when present. It deliberately ignores edits/business updates; routing those modes needs separate business context and authorization. `--self-test` checks the builder before creating any Telegram client.

## Reliability and state

Store dialog state separately from orders or other transactional records. A shared DbContext cannot be used concurrently across handlers; create a scoped unit of work per operation. Serialize conflicting state changes or use database concurrency controls. Parameterized SQL and migrations belong in the application's data layer.

The tagged client has configurable retry behavior for 429 responses; inspect its thresholds/count rather than layering an unbounded retry around every send. A network timeout may leave an uncertain send outcome. Handle known API errors by code/context and sanitize logs. Cancellation should reach API, database and upstream-generation tasks, while accepted durable jobs remain recoverable. Record known sent message IDs where application replay decisions need them.

## Validation

Compile against the selected package/runtime, unit-test dispatch and authorization with a fake client/transport, and cover duplicate updates, callbacks, cancellation, transient failures and persistent state. Verify webhook serialization and secret rejection with request fixtures. Actual Telegram rendering, reception and deployment need a separate controlled integration test.

For a symptom-specific investigation, use [diagnostics](troubleshooting.md). The 2026-10-04 focused audit source-checked the new builder/test against tagged types; this local host had no .NET SDK, so native build/self-test results belong in the repository validation report.
