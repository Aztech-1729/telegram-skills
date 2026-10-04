# Native drafts and edit-based streaming

Checked against [Telegram AI features](https://core.telegram.org/api/bots/ai) and the Bot API 10.3 reference on 2026-10-04. SDK support may lag the server feature; inspect the installed framework's raw-request path before adapting code.

## Native draft lifecycle

Use `sendMessageDraft` for regular text and `sendRichMessageDraft` for rich content in the supported private-chat context. Supply a nonzero `draft_id`, preserve it across successive updates, and carry `message_thread_id` when applicable. Finalize with `sendMessage` or `sendRichMessage`; drafts are temporary previews, not durable messages.

Maintain a registry keyed by the generation's scoped identity. Coalesce partial output on an application-defined schedule and retain the latest partial result; do not submit every model token independently. On `stopped_message_generation`, stop the corresponding task and upstream generation, then follow the requested stop/persistence policy. The stop of one topic must not cancel another user's request.

The payload builder includes `can_stop` and `keep_on_stop` where requested. A stopped draft or failed send should not imply that a payment/order action was canceled or completed; coordinate business actions separately.

```text
start scoped generation
  -> consume chunks -> coalesce -> update same draft
  -> stop update: cancel matching task and upstream request
  -> normal completion: send final persistent result
  -> failure: show a bounded recoverable status; retain application outcome
```

## Fallback by editing an ordinary message

Send a placeholder; update it only when content changed and the application throttle allows it. Keep one awaited edit in flight per message. Handle `retry_after`, skip benign “message is not modified,” and stop or reopen the view if the message was deleted. A hardcoded one-edit-per-second rule is an example policy, not a guarantee against every limit.

Partial generated markup is often invalid. Send partial text without a parse mode, or use a renderer that always produces balanced markup. On completion, render the complete content and split/attach long output deliberately. Avoid truncating the final answer silently to the first 4000 characters.

## Transport failure and duplicate outcome

A timeout can occur after Telegram accepted a send. Reissuing a final send may duplicate it. Decide whether to retry based on method and application outcome, store the message identity when known, and make any business side effects independent/idempotent. Rate-limited draft retries can normally use the latest state rather than replaying every old partial update.

## Offline validation

Test payload shape, nonzero draft IDs, one rich representation, cancellation scoping, coalescing and finalization decisions with a fake transport. Live Telegram client appearance and delivery remain separate acceptance checks. See `assets/payloads.py` and `tests/test_payloads.py` for deterministic payload checks.
