# grammY and Telegraf diagnostics

Focused source review: **2026-10-04**, against grammY 1.46.0 and Telegraf 4.16.3. Start from a synthetic failing update and the installed dependency/lockfile, then use the matching framework row.

| Symptom | Check and repair |
| --- | --- |
| Command works privately but not in a group | Inspect command entities/mentions and BotFather privacy mode. Test `/help@YourBot` with that bot's identity; a broad text handler registered first can consume the command. |
| A callback spins or fails when used from inline mode | Acknowledge even an expired/rejected action. Inline callbacks can have `inline_message_id` without a chat/message: use the inline edit path or notification text; `ctx.reply` needs a chat. The starter handles both variants. |
| Replies leave a forum topic | At these pins, both `ctx.reply` implementations preserve a source topic. Direct `ctx.api.sendMessage`/`ctx.telegram.sendMessage` calls need explicit routing fields. Store chat and topic together when scheduling later replies. |
| State changes disappear under load | In grammY runner install `sequentialize` before session middleware, with the same resource keys. In Telegraf verify the installed session implementation and protect application read-modify-write operations. Shared storage alone does not make concurrent business updates atomic. |
| One bot becomes unresponsive during file/DB work | Built-in grammY polling processes middleware sequentially. Consider runner plus resource serialization; bound work rather than dropping `await`. Telegraf's `handlerTimeout` rejects the handler promise, but that timeout does not cancel the underlying job. |
| Webhook says 200 while an operation failed | A catch handler that only logs makes the middleware appear handled. Choose an ingress/durable-inbox policy that distinguishes accepted work from lost work. grammY passes webhook errors to the HTTP framework; Telegraf's catch hook runs inside `handleUpdate`. |
| A current method exists in Telegram docs but not the SDK | Inspect the pinned types and tagged implementation. Telegraf's hosted TypeDoc can show an older version. Upgrade or isolate a tested raw adapter; suppressing TypeScript errors does not add runtime methods. |

## Polling lifecycle

`start`/`launch` switch reception to polling and delete the webhook. Use a separate worker entrypoint and make that transition deliberate. Neither starter requests queued-update deletion.

grammY `stop()` returns a promise and can make a final offset-confirmation request. Catch shutdown failures and wait for the `start()` promise when draining middleware. Telegraf `stop()` throws before its polling/server exists; its launch callback runs before polling is created. The entrypoint exits immediately only for that pinned pre-receiver condition, where there is no handler work to drain. A production supervisor still needs startup deadlines and an accepted-job drain policy. Real signal timing is separate from the request fixture tests.

## Small regression set

Run `npm ci --ignore-scripts` and `npm test` in the starter. The local fake API verifies command order, prompt callback acknowledgment, source-topic payloads, plain text, inline/stale callbacks, and ignored edits/media. Add application tests for session races, authorization, webhook retries and shutdown; these are not proved by the echo fixture.
