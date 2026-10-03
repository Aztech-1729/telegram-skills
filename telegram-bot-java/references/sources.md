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

The original EchoBot.java passed **javac --release 17** using **JDK 21.0.12.1 on Windows**, against the published TelegramBots 10.3.0 client/longpolling/meta jars and Jackson annotations 2.17.2. This checked imports, consumer class, builders and execute/register signatures.

Maven was not available, so Maven package/plugin resolution and a complete runtime classpath were not exercised. Pengrad's illustrative fragment was source-checked, not compiled. No Java program was started and no Telegram request, webhook registration or payment operation was made.

Build the complete application with its selected dependency manager before running it; compilation is separate from live token/permissions/delivery validation.
