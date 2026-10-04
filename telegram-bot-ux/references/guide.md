# Chat interaction and button decisions

Reviewed 2026-10-04. The following product choices are recommendations, not new
Telegram restrictions. Preserve a user's specified brand, locale and workflow.

## Pick the interaction surface

| Task | Starting choice | Reason / limitation |
|---|---|---|
| Act on a particular message, settings, pagination | Inline keyboard | Keeps the action next to its subject without sending a text reply |
| Answer one small question or request native contact/location | Reply keyboard | Constrained input; ordinary labels become chat messages |
| Enter a title or other free text | Correlated reply / ForceReply | Makes the expected input visible; correlate user, chat and prompt |
| Search and share into another chat | Inline mode | User selects the target; don't expose private results through shared caching |
| Edit many fields, compare a large catalog, use custom layout | Mini App | Browser UI can justify its extra load/auth/context handling |

A reply keyboard label is input, not proof the sender clicked a trusted control.
Keep visible /help and /cancel or equivalent affordances when the flow needs them.
Commands are useful shortcuts; do not make ordinary users memorize argument syntax.

## What color belongs to which button?

Native inline/reply buttons accept `primary`, `success`, `danger` or an omitted
style. Telegram specifies blue, green and red respectively; omitted style is
client-specific. The exact hue, contrast and rendering remain client-controlled.
Rich Message buttons have their own schema: `link` styling is callback-only, not a
URL button style. Ordinary keyboards do not gain that value. Mini App CSS and
BottomButton color APIs are separate.
[Native schema](https://core.telegram.org/bots/api#inlinekeyboardbutton)

| Role | Suggested style | Example | Avoid |
|---|---|---|---|
| Main next action | `primary` | Continue, View basket, Review booking | Making every option blue |
| Positive commitment | `success` when helpful, or the normal primary CTA | Confirm reservation, Enable reminders | Green implying a payment already succeeded |
| Irreversible/destructive action | `danger` | Delete saved project, Revoke access | Red Cancel, Back, Close or a harmless reset of filters |
| Navigation / dismissal | Omit style | Back, Cancel, Close, Previous, Next | Treating dismissal as destruction |
| Equal peer choices | Omit style consistently | English / Urdu; Standard / Express | Coloring one choice as objectively correct without a reason |
| Permission request | Contextual normal/primary action | Share phone number | Green pressure to consent; red refusal |
| Checkout | Normal/primary action with amount and currency | Pay 50 Stars | "Free" or "Done" before the server confirms settlement |
| External link | Default native URL button or a supported Rich Message URL style | Read terms, Open receipt | `link` styling on any URL button; guessed RGB on native keyboards |

As a starting hierarchy, emphasize one main action per decision and leave peer
choices neutral. This is not an API limit. Use readable verbs and objects:
"Delete reminder" communicates more than "Yes"; "Keep reminder" more than "No".
Shorten layout before shrinking meaning. Test translations and narrow clients.

## Screen and state contract

For each view specify: subject, user goal, visible information, allowed actions,
owner/context, transition, effect and recovery. Store durable business state
separately from transient UI state. A saved navigation position may expire without
losing a paid order or submitted form.

| State | Explain | Useful action / invariant |
|---|---|---|
| Empty | What is missing, how to start | Add first item / Clear filters, not unexplained blank space |
| Loading | What is happening | Acknowledge taps; prevent duplicate commits; allow meaningful cancellation |
| Invalid input | Which field and how to correct it | Preserve other values and leave the flow active |
| No permission | What access is required | Back / Request access; don't leak another user's object |
| Expired menu | Data or interaction is stale | Reopen fresh authorized view; no action from stale payload |
| Retryable failure | What remains saved | Retry the safe read or reconcile a write's outcome |
| Unknown write outcome | Completion isn't known yet | Check status using the operation/order ID before resubmission |
| Completed | What actually changed | Receipt/result and next action; remove obsolete commit controls |

An enabled-looking button is not authorization. Recheck object ownership, current
permissions, price, expiry and version in the handler. Answer callbacks promptly
even when rejecting them. A loading indicator is feedback, not durable delivery.

## Navigation, groups and recovery

- Keep Back within the journey; keep Home or /start available where users need a
  fresh entry. Don't let Back silently undo a completed business operation.
- Store multi-step state under the relevant bot/user/chat/topic identity. Decide
  what a second device, simultaneous flow or restart does to the first view.
- In groups, a shared message may be seen and tapped by many users. Either scope
  ownership explicitly or design a genuinely shared action with its own permissions.
- Revalidate forwarded messages and old buttons. Reopen private work in the user's
  bot chat when the task needs privacy, and provide a usable deep-link fallback.
- Confirmation should name the object and consequence. Prefer undo for cheap
  reversible changes; use an explicit confirmation for meaningful irreversible loss.
- Explain permission requests before invoking them and handle denial as a normal
  branch. Avoid requesting contact, location or write access unrelated to the task.

## Microcopy and localization

Say what the user can do now: "This menu expired. Open your current orders." Keep
internal exception names and token details out of user messages. For support,
provide a non-secret reference ID where useful. Use the user's language preference;
language_code is a hint, not a permanent identity. Use plural/currency/date formatting,
numeric IDs for identity and locale-specific button order only after checking the
actual locale. Avoid emoji-only labels and country flags as language labels.

## Acceptance

Walk the main task, Back/Cancel, second tap, failed request, restart, denied access,
expired menu and long translated label. Inspect the final record and the visible
message together. Record which clients and accessibility tools were actually used;
offline payload tests cannot establish their appearance or usability.
