# Primary sources

Checked 2026-10-03.

- [NuGet 22.10.3.2](https://www.nuget.org/packages/Telegram.Bot/22.10.3.2): stable package, published 2026-09-25, target frameworks and package metadata.
- [Client at v22.10.3.2](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/TelegramBotClient.cs): event delegate signatures, dispatch and cancellation/retry implementation.
- [Quickstart](https://telegrambots.github.io/book/1/quickstart.html): current GetMe setup.
- [First chat bot](https://telegrambots.github.io/book/1/example-bot.html): message event pattern and SendMessage usage.
- [Project examples](https://github.com/TelegramBots/Telegram.Bot.Examples): host-specific example lookup; not a bundled guarantee.

The NuGet registration feed was checked for release timestamps. Its stable package is newer than the GitHub Releases page; the latter alone would incorrectly select 22.4.4.

## Focused event/routing audit: 2026-10-04

The NuGet page, quickstart and tagged client above were reread. The generated [Message model](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/Types/Message.cs), [DirectMessagesTopic model](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/Types/DirectMessagesTopic.cs), [SendMessageRequest](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/Requests/Sending%20Messages/SendMessageRequest.cs), [ChatId](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/Types/ChatId.cs), and [generated methods](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.2/src/Telegram.Bot/TelegramBotClientExtensions.ApiMethods.cs) verify the request builder, event variants and retry bounds.

The source audit is separate from the NuGet page's pending automated content observation: that marker remains until its changed source hash is explicitly compared and acknowledged. This local host had no .NET SDK; build/self-test execution is recorded separately from source review. No Telegram client was run during this audit.

## Focused package migration: 2026-10-09

- [NuGet 22.10.3.3](https://www.nuget.org/packages/Telegram.Bot/22.10.3.3): listed stable package published 2026-10-09; package metadata and its embedded repository commit match tag `v22.10.3.3` at `d16393f43ca8b00c39f52af665bf8cb712f11708`. Target frameworks and dependency requirements are unchanged from .2.
- [Client at v22.10.3.3](https://github.com/TelegramBots/Telegram.Bot/blob/v22.10.3.3/src/Telegram.Bot/TelegramBotClient.cs): unchanged event dispatch, cancellation and request/retry behavior used by the starter and guide.
- [Complete .2 to .3 comparison](https://github.com/TelegramBots/Telegram.Bot/compare/v22.10.3.2...v22.10.3.3): three commits affecting four files, adding media-interface getters and implicit rich-message conversions and correcting `HtmlText.PlainLength` for supplementary Unicode characters. Custom implementations of the affected interfaces need the added getters; the starter uses the package's existing message/request types.

The current NuGet stable feed and older .2 package page now expose .3; the starter pin and current guide were updated after comparing the exact tagged source with the published package. The starter restored and built with .NET SDK 8.0.425 without warnings or errors, and its existing offline echo-routing self-test passed before token lookup/client creation. This focused migration does not advance the earlier full guide or event/routing audit dates. No Telegram client was run.
