# grammY dialogs, replay and recovery

Reviewed 2026-10-04 with grammY **1.46.0** and `@grammyjs/conversations`
**2.1.1**. The [official guide](https://grammy.dev/plugins/conversations) is the
API authority. The plugin has its own version and storage contract.

## Choose the state model

| Interaction | Starting point |
|---|---|
| A command that finishes in one update | Ordinary handler |
| Callback screens with explicit states | Session/state machine plus authorized callback records |
| Ask, wait, validate and confirm a finite dialog | Conversations plugin |
| Scheduled delivery, payments or long-running jobs | Durable application records/queue |

Keep settings, orders and authorization in application storage. Conversation
storage holds replay data, including updates and external results; choose its
retention and access rules. Terminate dialogs rather than accumulating an
indefinite replay history.

## Tested private-chat factory

[feedback_bot.mjs](../assets/starter/feedback_bot.mjs) supplies a finite
`/feedback` → text → `/confirm` or `/cancel` flow. It accepts up to three text
attempts and three confirmation attempts, rejects group entry and checks the
actual sender. Its conversation store is **memory only**. Non-text updates are
filtered by `waitFor`; they do not consume the text-attempt budget.

The application supplies:

- `canSubmit(owner)`: a bounded asynchronous account check returning a JSON boolean.
- `saveFeedback({key, owner, text})`: transactional persistence returning
  `{saved: true}` only after commit. Recheck current permission here; the earlier
  account result is cached by replay and can become stale.

The per-entry key includes bot ID, user ID and entering update ID. Store it under
a unique constraint **with the feedback write in the same transaction**. A
duplicate key returns its committed receipt. An exception/timeout does not prove
the write failed; the example gives recovery copy without claiming success or
automatically creating a fresh submission.

Integrate the factory in the project's existing transport. Supply the configured
token/options and actual backend operations; importing it does not start polling
or deploy a database. Keep one conversations middleware and deliberate
registration order. Persistence, quotas and a saved-feedback lookup need
application implementations.

Run `npm ci --ignore-scripts` and `npm test` in the starter. Five tests use the
real plugin through a local fake Bot API: cached account reads, no repeated
prompts during replay, confirmation before saving, cancellation, text bounds,
private-chat isolation, denied accounts/groups and ambiguous backend errors.
These do not establish restart recovery, distributed serialization or live clients.

## Replay boundaries

| Operation inside a conversation | Boundary |
|---|---|
| Database/network operations, external state, time or randomness | `conversation.external`, or documented `now`/`random` helpers |
| `ctx.reply` and API calls through the conversational `ctx.api` | Await directly; the plugin records them |
| API calls through a separate `bot.api` instance | External operation, outside conversational API instrumentation |
| Outer session state | Access through `conversation.external`; absent from the inner context |

Return JSON-safe values. Database handles, streams and credentials should not
become persisted replay data. Use custom serialization only with an understood
stored representation.

Replay caching is **not crash-proof exactly-once delivery**. A process can commit
the external effect and die before persisting its replay result. Writes/payments
still need durable idempotency; message sends can have uncertain outcomes. Do not
wrap conversational `ctx.reply` in `external` as a generic replay fix.

## TypeScript context boundaries

The outer context has conversation controls. The inner context has only plugins
installed inside that conversation. This is a type integration fragment:

```ts
import type { Context } from "grammy";
import type { Conversation, ConversationFlavor } from "@grammyjs/conversations";

type OuterContext = ConversationFlavor<Context>;
type InnerContext = Context;
type FeedbackConversation = Conversation<OuterContext, InnerContext>;
```

Use `Bot<OuterContext>` for outer middleware and
`(conversation: FeedbackConversation, ctx: InnerContext)` for the builder.
Add an inner flavor only with its matching middleware in the conversation's
`plugins` option. `ctx.conversation` belongs to the outer context. Capture
validated entering identity; use each returned update for subsequent input.

## Cancellation, expiry, restart and concurrency

Handle cancellation inside a wait that would consume the command; a `/cancel`
handler after that conversation is insufficient alone. Cancellation before commit
differs from undoing committed work. The factory handles cancellation at both
steps and sets a five-minute `maxMillisecondsToWait` default.

Wait expiry is evaluated **when a later update arrives**. It does not wake a
worker at five minutes or guarantee an expiry notification. Required deadline
actions need a scheduler. Expired updates continue through outer middleware;
provide a suitable fallback.

Connect a supported storage adapter for restart continuity and version replay
data alongside changes to builder code. A version mismatch does not semantically
translate an old business draft: define user recovery and preserve committed
records separately. Namespace shared storage by bot, dialog and the chosen
chat/user/topic scope. Match serialization keys to storage keys before enabling
runner concurrency. Multiple processes require cross-process coordination.

Before production, test restart between steps, revocation before confirmation,
duplicate accepted updates, failed receipt replies, expiry and competing workers.
The backend owns the final authorization/commit boundary.
