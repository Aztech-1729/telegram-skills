---
name: telegram-bot-java
description: Build or repair Java HTTP Telegram Bot API bots using TelegramBots or Pengrad, including polling, webhooks, update dispatch, callbacks, media, and dependency/API migration.
---

# Java Telegram Bot API

Use for Java HTTP bots. Select TelegramBots for its modular client, polling/webhook, and Spring integrations; select Pengrad for a compact request/response API when it fits the project. Neither library is an MTProto user-account client.

## Workflow

- Read [the Java guide](references/guide.md) for version selection, request objects, update consumers, callbacks/media, webhooks, concurrency, and the differences between the two libraries.
- Match imports and dependency modules to [the checked sources](references/sources.md). Modern TelegramBots uses TelegramClient and separate update-reception modules; old TelegramLongPollingBot tutorials use a different architecture.
- Keep the project's existing framework and build system when appropriate. Align TelegramBots module versions and verify newly introduced API fields before using them.
- Read tokens from configuration; authorize sensitive actions using server-side state. Treat callbacks and Mini App data as untrusted inputs.
- Select one update-delivery owner, persist business state, and handle API failures without silently acknowledging lost work.
- Build the application and test dispatch/error handling without contacting Telegram. Report any absence of runtime or integration validation.

## Starter

[assets/echo/pom.xml](assets/echo/pom.xml) and [EchoBot.java](assets/echo/src/main/java/EchoBot.java) form an original plain-text polling example using TelegramBots. It reads TELEGRAM_BOT_TOKEN. Running it contacts Telegram; compilation does not.

Use the feature guides for keyboards, payments, Mini Apps, and deployment, adapting their wire concepts to the chosen Java SDK.
