# PHP SDK ingress and worker diagnostics

Focused source review: **2026-10-04**, irazasyed SDK 3.16.0. Preserve an existing Longman application; its command/database flow is a different API.

| Symptom | Check and repair |
| --- | --- |
| Webhook code loops over nonexistent updates | Tagged `getWebhookUpdate()` returns one UpdateObject, despite historical prose describing an array. A webhook request contains one update; only polling produces a batch. |
| Laravel works locally but uses stale credentials | Check the selected Laravel version's config caching and queue-worker restart behavior. Put token/SDK configuration in config services; long-lived workers do not reload environment changes per job. |
| 403 even with a valid payload | Confirm the dedicated secret set during webhook registration reaches the endpoint unchanged through the proxy. Check the header before parsing. A public route must not contain the bot token. |
| 500 on malformed JSON before SDK handling | Decode a bounded body with JSON_THROW_ON_ERROR and verify numeric update/chat IDs before client calls. The starter isolates ingress validation in WebhookInput.php so rejection tests need no Composer packages or credentials. |
| An echo moves out of a forum topic | Add `message_thread_id` for an actual topic message; do not confuse it with the chat or message ID. The starter tests both the topic and plain-text request shape. |
| Duplicate replies after a 503/time-out | Telegram can retry a webhook. The starter has no durable inbox/outbox; storing only an in-memory update ID is insufficient across PHP workers/restarts. Accept and deduplicate consequential work transactionally, then use a durable queue. |
| A current endpoint has no wrapper method | Check tagged method traits. At this pin public `post(endpoint, params)` performs a raw form request; it is not a new typed object model. Preserve the SDK response/error contract and test the required parameters, or isolate an HTTP adapter. |

## Worker and logging boundary

Give queued work explicit request/connect timeouts, bounded retries and a restart policy. PHP request termination is not job cancellation or fulfillment. Do not echo exceptions to Telegram's HTTP request; log safe error classes/correlation IDs instead of URLs/payloads. File streams must remain valid through the SDK upload and close afterward.

## Fixture checks

Run `php test.php` in the starter before Composer installation. It checks method/secret/size/JSON rejection ordering, invalid IDs, source-topic payloads and ignored non-message/edit updates. It does not call the SDK or prove hosting, durable deduplication or file/payment methods. Lint all PHP files and resolve Composer separately for those paths.
