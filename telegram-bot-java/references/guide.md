# Java Telegram bots: implementation reference

Checked **2026-10-03**. See [sources.md](sources.md) for versioned sources and validation scope.

## Contents

Library selection; dependencies and starter; updates/requests; callbacks/media; errors and pacing; webhook/Spring integration; state/concurrency; migration; verification.

## 1. TelegramBots or Pengrad

| Library | Select when | API style |
| --- | --- | --- |
| TelegramBots by rubenlagus | Modular polling/webhook reception, request objects, Spring integration | TelegramClient.execute(method); model getters and builders |
| Pengrad java-telegram-bot-api | Compact client and listener/request integration | TelegramBot.execute(request); fluent options; response.isOk() |
| Existing MTProto Java client | User-account actions rather than an HTTP bot | Separate account/session protocol; these libraries do not provide it |

Both checked Java releases are **10.3.0**. That matching number is a project-specific API version convention, not proof that future server features exist. TelegramBots' current source targets **Java 17**. Use the chosen artifact's POM/release requirements instead of an old Java 8 tutorial.

Keep an existing framework when it meets the user's task. Avoid importing both libraries' SendMessage or Update classes into the same implementation without explicit adapters.

## 2. Dependencies and original starter

[assets/echo/pom.xml](../assets/echo/pom.xml) aligns:

```xml
<dependency>
  <groupId>org.telegram</groupId>
  <artifactId>telegrambots-longpolling</artifactId>
  <version>10.3.0</version>
</dependency>
<dependency>
  <groupId>org.telegram</groupId>
  <artifactId>telegrambots-client</artifactId>
  <version>10.3.0</version>
</dependency>
```

The [original EchoBot](../assets/echo/src/main/java/EchoBot.java) uses DefaultLongPollingUpdateConsumer, OkHttpTelegramClient, and TelegramBotsLongPollingApplication. It replies with plain text in the source topic, owns the scheduled polling executor and stops it during JVM shutdown. It reads TELEGRAM_BOT_TOKEN. Consumer queue draining and durable receipt are separate service concerns; see [diagnostics](troubleshooting.md).

Copy the asset directory into the application's chosen location. `mvn verify` compiles it and runs the offline fixture tests; `mvn exec:java -Dexec.mainClass=EchoBot` deliberately starts polling after configuration. Running registers/connects a real bot; documentation checks must not execute it.

TelegramBots separates the HTTP client from the update receiver. Old TelegramLongPollingBot/TelegramBotsApi tutorials belong to a different generation and cannot be combined with the modular setup by renaming one import.

LongPollingSingleThreadUpdateConsumer is deprecated in the checked source because its executor is shared. DefaultLongPollingUpdateConsumer owns a per-instance executor and has a close lifecycle. The asset was compiled against the published 10.3.0 jars, including this class.

## 3. Update variants and routing

An Update can contain a message, edit, channel post, callback, inline query, membership change, pre-checkout query, successful-payment message, or newer event. hasMessage()/hasText() apply only to the relevant variant. Do not dereference getMessage() for callback-only updates.

Route commands and callbacks deliberately, using server-side authorization for administration and purchases. A command registered with BotFather is discoverability metadata, not authorization.

A single-threaded consumer is convenient for ordered local processing, but slow HTTP/DB work blocks its queue. For independent work use a bounded executor or durable job queue with a clear per-chat/operation ordering policy. Persist receipt/effects before acknowledging work that must survive a crash.

If adding an SDK command extension, check its module and event contract at the pinned release. The base client is not automatically an FSM, scheduler or durable task system.

## 4. Request models and sends

TelegramBots methods are objects such as SendMessage, AnswerCallbackQuery, SendPhoto and SetWebhook. Execute them through TelegramClient. Builders supply required and optional fields; handle TelegramApiException rather than assuming a return indicates business completion.

For media, use the appropriate InputFile variant and preserve stream/file lifetime until the request finishes. Reuse file_id when suitable. Escape user-provided values under HTML/Markdown or send plain text. Builder names are Java API conventions; wire method names remain sendMessage and similar Bot API names.

TelegramBots 10.3.0 has a checked type mismatch: received DirectMessagesTopic.topicId is Long, but SendMessage.directMessagesTopicId is Integer. The starter accepts only positive representable values and rejects overflow without truncation. For larger topic IDs, select a corrected SDK or a tested wire adapter; never blindly cast a Telegram identifier.

For callback buttons, construct an InlineKeyboardMarkup containing InlineKeyboardButton rows. A callback acknowledgement is a separate AnswerCallbackQuery request. Check callback data, requesting user, chat/message ownership and expiry against application state before changing an order or permission.

Mini Apps use WebAppInfo/menu/inline-keyboard launch structures. Validate initData on the backend, independently of Java request construction. Payment pre-checkout and successful-payment updates have different responsibilities; consult the payments guide.

## 5. Pengrad differences

Dependency coordinates:

```xml
<dependency>
  <groupId>com.github.pengrad</groupId>
  <artifactId>java-telegram-bot-api</artifactId>
  <version>10.3.0</version>
</dependency>
```

A request fragment for an existing client and known chat ID is:

```java
com.pengrad.telegrambot.response.SendResponse response =
    bot.execute(new com.pengrad.telegrambot.request.SendMessage(chatId, "Hello"));
if (!response.isOk()) {
    throw new IllegalStateException("Telegram refused the send: " + response.errorCode());
}
```

Here bot is com.pengrad.telegrambot.TelegramBot. This fragment is not a full receiver/application.

Pengrad models commonly use update.message()/message.chat().id(), whereas TelegramBots uses getters. Its sync and asynchronous execute variants require separate error paths. Async callbacks must handle onFailure; a Telegram error response is distinct from a transport exception.

setUpdatesListener supplies batches of updates. The listener returns the last processed ID or a confirmation constant. Confirm all only after the application's intended processing/durable receipt. Returning CONFIRMED_UPDATES_ALL while failures were silently dropped can lose work. Retries can repeat effects; maintain idempotent operation records where needed.

For manually receiving updates use GetUpdates and offset = last processed update ID + 1. For webhooks parse Update with the SDK's documented parsing helper, then dispatch through the application's existing path. Do not concurrently run the listener and webhook receiver.

## 6. Errors and pacing

Identify SDK-specific error/response types, then classify:

- Wrong token or permissions: correct configuration/account access.
- Invalid parameters/entity parsing: fix the request rather than retrying it unchanged.
- 429: honor retry_after, with bounded attempts and a scheduled delay.
- Network timeout: delivery can be uncertain; use a deduplication/outbox policy for effects that matter.

Pengrad BaseResponse exposes parameters(), whose nullable retryAfter() contains a server retry delay when supplied. TelegramBots exceptions/responses have their own accessors: inspect the chosen method/client release rather than pasting Pengrad syntax.

Avoid sleeping on the only update-consumer thread for a broadcast. Use a bounded scheduler and store retry state for durable outgoing jobs. Do not log request URLs containing tokens or raw personal/payment data.

## 7. Webhooks and Spring

TelegramBots provides separate webhook and Spring starter modules. Select the matching longpolling or webhook starter for an existing Spring application, align versions, and avoid manually creating a second receiver for the same token.

A webhook deployment needs HTTPS/reachable routing, setWebhook configuration, allowed updates, and X-Telegram-Bot-Api-Secret-Token verification. The application's ingress should reject incorrect/missing secret before parsing or queuing the update.

Verify how the chosen module registers routes and sets/deletes webhooks. Do not assume that instantiating TelegramClient starts a server. A controller that receives JSON also needs lifecycle, size limits, timeout, queue/response behavior and shutdown handling.

Preserve update_id in the inbox and return an appropriate HTTP status based on the application's durable receipt policy. Telegram can retry deliveries; handlers must tolerate duplicates.

## 8. State, schedules, and concurrency

Use long for numeric Telegram chat/user IDs; IDs exceed 32-bit ranges and chat IDs can be negative. Keep username/display name separate from identity.

Dialogues, scheduled reminders, orders and entitlements belong in durable storage when required. In-memory maps are appropriate only for deliberately transient state. Database access must follow the application's thread-safety and connection-pool rules.

Java's concurrency tools do not remove API limits. Bound work, propagate deadlines, scope state correctly, and make shutdown drain or persist pending tasks according to the application contract.

## 9. Migration checklist

For a Java library/version migration, recheck artifact names, request-builder fields, nullable update variants, exceptions versus error responses, callback routing, file uploads, webhook registration and executor ownership.

Compile against the project's selected release. For current Bot API fields missing from that release, upgrade deliberately or isolate a small raw-HTTP adapter; do not invent SDK methods. Cross-language recipes provide a design, not import-compatible Java code.

## 10. Verification

On 2026-10-04 the asset passed full `mvn verify` with Maven 3.10.0/JDK 21, compiling for Java 17 and running four offline fixtures through a substituted TelegramClient. This checks forum/direct-message routing, large-ID refusal, plain text and ignored update variants. Live polling was not started.

For an application, compile its whole dependency graph, test dispatch with deserialized fixtures and mock client requests, then verify webhook secrets locally. Live token/permissions, media, payments and delivery tests require an explicitly configured test environment.
