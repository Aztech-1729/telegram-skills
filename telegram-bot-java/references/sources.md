# Sources and validation

**Research cutoff and review date: 2026-10-03.**

## Checked versions and scope

| Project | Checked release | Scope |
| --- | --- | --- |
| rubenlagus/TelegramBots | 10.3.0 | Published client/meta/longpolling artifacts; source Java target 17 |
| pengrad/java-telegram-bot-api | 10.3.0 | Request/response/listener conventions and callback/media/webhook guidance |

No universal promise of later Bot API support is made. Matching API-version release numbers do not replace inspection of required methods/fields.

## Primary sources

- [TelegramBots release v10.3.0](https://github.com/rubenlagus/TelegramBots/releases/tag/v10.3.0): release baseline.
- [TelegramBots source](https://github.com/rubenlagus/TelegramBots): modular library organization, pom.xml Java/version requirements, client and polling lifecycle.
- [Official echo lesson](https://rubenlagus.github.io/TelegramBotsDocumentation/lesson-1.html): TelegramClient/OkHttpTelegramClient and separate longpolling/client dependency structure. Its older consumer-interface example was checked against current source/artifacts.
- [DefaultLongPollingUpdateConsumer source](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-longpolling/src/main/java/org/telegram/telegrambots/longpolling/util/DefaultLongPollingUpdateConsumer.java): per-instance executor and close contract.
- [LongPollingSingleThreadUpdateConsumer source](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-longpolling/src/main/java/org/telegram/telegrambots/longpolling/util/LongPollingSingleThreadUpdateConsumer.java): deprecation and shared-executor distinction.
- [Published longpolling POM](https://repo.maven.apache.org/maven2/org/telegram/telegrambots-longpolling/10.3.0/telegrambots-longpolling-10.3.0.pom), [client POM](https://repo.maven.apache.org/maven2/org/telegram/telegrambots-client/10.3.0/telegrambots-client-10.3.0.pom), and [meta POM](https://repo.maven.apache.org/maven2/org/telegram/telegrambots-meta/10.3.0/telegrambots-meta-10.3.0.pom): artifact availability and dependency graph.
- [Pengrad project README](https://github.com/pengrad/java-telegram-bot-api): fluent requests, execute callbacks, update confirmation and webhook parsing.
- [Pengrad response types](https://github.com/pengrad/java-telegram-bot-api/tree/master/library/src/main/java/com/pengrad/telegrambot/response) and [model sources](https://github.com/pengrad/java-telegram-bot-api/tree/master/library/src/main/java/com/pengrad/telegrambot/model): nullable parameters/updates and response status.
- [Telegram Bot API](https://core.telegram.org/bots/api): actual wire types, callback acknowledgement, webhook secret, permissions and API errors.
- [Bot FAQ](https://core.telegram.org/bots/faq): update delivery and bot operational constraints.

## Validation actually performed

The revised EchoBot passed **Maven 3.10.0 verify**, using **JDK 21.0.12.1 on Windows** and Java 17 compilation, on **2026-10-04**. The complete dependency graph resolved and four JUnit fixtures passed without a network TelegramClient. They cover forum routing/plain text, direct-message topics, overflow refusal and ignored update variants.

Pengrad's illustrative fragment remains source-checked, not compiled. No live Java receiver was started and no Telegram request, webhook registration or payment operation was made.

Build the complete application with its selected dependency manager before running it; compilation is separate from live token/permissions/delivery validation.

## Focused source audit: 2026-10-04

- [TelegramBots application lifecycle](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-longpolling/src/main/java/org/telegram/telegrambots/longpolling/TelegramBotsLongPollingApplication.java), [BotSession](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-longpolling/src/main/java/org/telegram/telegrambots/longpolling/BotSession.java), and the consumer source above: registration, offset timing, consumer close and scheduled executor ownership.
- [SendMessage model](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-meta/src/main/java/org/telegram/telegrambots/meta/api/methods/send/SendMessage.java) and [Message model](https://github.com/rubenlagus/TelegramBots/blob/v10.3.0/telegrambots-meta/src/main/java/org/telegram/telegrambots/meta/api/objects/message/Message.java): topic routing and the Long-received/Integer-send direct-topic mismatch, confirmed by compiling against the published artifacts.
- [Pengrad 10.3.0 UpdatesListener](https://github.com/pengrad/java-telegram-bot-api/blob/10.3.0/library/src/main/java/com/pengrad/telegrambot/UpdatesListener.java): confirmation constants/callback contract.

This focused audit preserves the earlier release/feature cutoff for sources not reread.

## Focused test-tooling migration: 2026-10-11

The starter's test-scoped `org.junit.jupiter:junit-jupiter` pin moved from 5.11.4 to 6.1.3. The official JUnit 6.1.3 overview, build support and release notes were reviewed, along with the published Maven artifact and the exact `Test`/`Assertions` APIs used by all four fixtures. [The guide](guide.md#2-dependencies-and-original-starter) links the runtime/build requirements. JUnit 6 requires Java 17 and Surefire/Failsafe 3.0.0 or newer; the existing Java 17 target and Surefire 3.6.0 satisfy them. All resolved JUnit test modules use 6.1.3.

An isolated copy passed Maven 3.10.0 `verify` with JDK 21.0.12.1, compiling for Java 17 and running all four unchanged offline routing tests with zero failures, errors or skips. Direct Python HTTPS captures of the documentation/Maven endpoint failed certificate verification on this host; official documentation was inspected through the web tool and Maven resolved the public artifact without disabling TLS verification. This is a focused test-tooling check, not an advance of the earlier Telegram SDK or lifecycle audit dates. No bot token, polling or Telegram request was used.
