# Concrete journey patterns

Adapt these original examples to the actual product; labels and row counts are
starting points, not Telegram constraints.

## First use and returning users

```text
/start
  "Save reminders and manage them here."
  [Create reminder — primary] [My reminders — default]
  [Help — default]
```

Returning users should be able to reach their existing records directly. Don't
repeat an onboarding questionnaire on every /start. Register short command
descriptions using the right scope/language and keep the fallback text useful.
An inline-only bot should still explain how to use it when opened in a private chat.

## Multi-step creation

```text
What should I remind you about?       [Cancel]
When? Show the timezone explicitly.  [Back] [Cancel]
Review: task, time and timezone.      [Save reminder — primary] [Edit] [Cancel]
Saved: actual scheduled time.         [View reminders] [Create another]
```

Validate before leaving each step; preserve good input. Expire a draft deliberately
and say how to restart. Persist the completed reminder before displaying success;
use durable scheduling and distinguish notification failure from record creation.

## Deletion

```text
Reminder details                     [Edit] [Delete — danger] [Back]
"Delete ‘Take medication’? Its future alerts will stop."
                                     [Delete reminder — danger] [Keep reminder]
Deleted after the authorized write.   [Back to reminders]
```

Bind the second action to the exact current reminder and owner. If it was already
deleted, report that result idempotently. For a reversible draft removal, an Undo
action may serve better than an extra confirmation. Don't call the initial delete
tap completed until the write succeeds.

## Digital checkout

```text
Product: title, included goods, current price.
  [Review order — primary] [Back]
Order: item, 50 Stars, buyer-relevant terms.
  [Pay 50 Stars] [Cancel]
Payment pending -> verified server payment -> fulfillment -> receipt.
  [Check status] / [Open purchase] / [Contact support], as appropriate.
```

The actual invoice pay button follows Telegram's first-button placement rule and
payment schema. UI colors don't prove settlement. Bind order, buyer, currency and
amount on the server; reconcile payment/delivery separately. A canceled invoice
closes that UI; it does not necessarily undo a previous successful purchase.

## Permission and stale-state branches

```text
"Share your location to find nearby pickup points. You can enter an address instead."
  [Share location] [Enter address] [Cancel]

"This page is no longer current. Your order is still saved."
  [Open current order — primary] [Home]
```

Offer alternatives only when the product actually implements them. Denial should
not loop a native permission prompt. Stale recovery opens fresh authorized state;
it does not replay an old checkout or destructive callback.
