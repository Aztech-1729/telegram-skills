# Java receiver and request diagnostics

Focused source review: **2026-10-04**, TelegramBots/Pengrad 10.3.0. Reproduce with an Update fixture and a substituted client before changing the receiver.

| Symptom | Check and repair |
| --- | --- |
| Old tutorial imports fail | TelegramBots' modular client and receiver are separate artifacts. Align client/meta/longpolling/Spring versions, inspect `mvn dependency:tree`, and remove accidental old transitive modules. |
| Polling shuts down but the JVM stays alive | At TelegramBots 10.3.0, `BotSession.close()` cancels the poll and closes the consumer; it does not shut down the supplied scheduled executor. The starter owns and stops that executor explicitly. Inspect other application/client worker threads too. |
| A failed handler update is never delivered again | The polling session tracks the highest received ID before background consumer work completes. Catching or throwing from that worker does not roll back Telegram's offset. Consequential work needs durable receipt before async handoff and recoverable processing; the echo only logs send failure. |
| Memory grows during slow sends | `DefaultLongPollingUpdateConsumer` uses a per-instance single-thread executor with an unbounded queue. Apply bounded acceptance/durable queuing where needed; preserve ordering for shared chat/user/order state. |
| Echo appears in General instead of the source topic | Set `SendMessage.messageThreadId` from an actual topic message. A chat ID alone is not a topic destination. The starter and fixture test preserve this field. |
| A direct-message topic cannot be passed to SendMessage | At 10.3.0 the received topic ID is Long but that request field is Integer. The starter range-checks before narrowing and refuses overflow. Use a corrected SDK/tested wire adapter if the required ID is not representable. |
| Callback handling throws on getMessage | The update may be callback-only, and a callback may reference an inline or inaccessible message. Acknowledge by query ID, then select a supported edit/send route after checking available fields. |
| Pengrad listener loses work | Its returned confirmation ID is an acknowledgment contract. Confirm only completed or durably accepted work; do not return `CONFIRMED_UPDATES_ALL` after silently dropping a failed item. |

## Receiver-specific lifecycle

TelegramBots' polling registration deletes a webhook. Perform that transport transition deliberately; a client constructor alone is not a receiver. Spring's polling/webhook starter should own reception when selected, rather than competing with a manual application instance.

Consumer `close()` calls executor shutdown; it is not a durable drain guarantee or deadline. For a service with accepted jobs, own the queue, stop intake, drain/persist according to the shutdown contract, and then release clients/executors. Do not infer daemon-thread behavior from comments: inspect the actual thread factory.

## Validate requests without a bot

`mvn verify` runs `EchoBotTest`: a deserialized forum fixture and a proxy TelegramClient verify large negative chat IDs, the topic field, plain text and ignored variants without transport. Extend fixtures for callback authorization and error classification. Compilation cannot establish bot rights, webhook reachability or SDK support for every later wire feature.
