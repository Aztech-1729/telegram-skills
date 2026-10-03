---
name: telegram-bot-dotnet
description: Build or maintain C#/.NET Telegram HTTP Bot API applications with Telegram.Bot, including async message/update handlers, polling, ASP.NET Core webhooks, cancellation, files, state and current API compatibility. Use for .NET projects; this is not an MTProto user-client guide.
---

# Telegram.Bot for .NET

Checked **2026-10-03**: NuGet stable baseline **Telegram.Bot 22.10.3.2**, published 2026-09-25. The GitHub Releases page is older than the NuGet stable feed; use package metadata and matching tagged source when verifying an API.

Read [implementation guide](references/guide.md) for lifecycle, webhook hosting, routing, retries and persistence. [Sources](references/sources.md) record the primary checks.

## Implement with one lifecycle

- Use the existing project's .NET/runtime, package version, hosting and dependency injection conventions.
- Configure `TELEGRAM_BOT_TOKEN` through environment/configuration; fail clearly without displaying it.
- Choose one reception model: client event-based polling, explicit receiver/polling infrastructure, or webhook-fed updates. Do not combine polling models or poll while a webhook is configured.
- Route non-message updates explicitly. `OnMessage` is not a callback/payment/inline handler; inspect the tagged client's event dispatch semantics.
- Await operations and pass cancellation through the service lifecycle. Avoid blocking `.Result` / `.Wait()` in async handlers.
- Scope application state and authorize commands/callbacks separately from the transport.

## Starter

[Program.cs](assets/starter/Program.cs) and [project file](assets/starter/TelegramStarter.csproj) provide an event-based text echo with environment configuration and cancellation. It handles original messages, not edits/business messages automatically. It logs error type rather than token-bearing exception text.

```bash
cd telegram-bot-dotnet/assets/starter
dotnet build
dotnet run
```

A .NET 8 SDK is required to build the starter. Its API signatures were checked against tagged source; compilation is recorded separately in the repository validation report. Real execution requires bot credentials and Telegram access.

## Integration rules

Use a scoped database unit of work per operation; a singleton bot client does not make a shared DbContext safe. Validate webhook secrets and duplicates, check bot/user permissions, and make payment fulfillment durable. Match newer fields/methods to the installed package rather than translating Python names into C# guesses.

Load the shared [UI](../telegram-bot-keyboards-ui/SKILL.md), [payments](../telegram-bot-payments-stars/SKILL.md), [Mini Apps](../telegram-bot-miniapps/SKILL.md), [rich messaging](../telegram-bot-rich-messaging/SKILL.md), and [operations](../telegram-bot-advanced-features/SKILL.md) guides as needed.
