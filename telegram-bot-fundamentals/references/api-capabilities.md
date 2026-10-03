# Telegram capability routing and integration decisions

Checked **2026-10-03**, against the Telegram feature guide, Bot API 10.3 reference, and topic guides. This map covers feature families relevant to application design; consult the linked reference for the full method/schema inventory.

## Traditional Bot API domains

| Domain | Implementation decisions | Specialist reference |
| --- | --- | --- |
| Messages, replies, edits, forwarding/copying | Choose the content type; preserve destination/topic context, reply metadata and formatting. | [Messages](https://core.telegram.org/bots/api#available-methods); rich-messaging skill. |
| Photos, audio, video, documents, albums and live photos | Choose file IDs versus upload; check method-specific media and caption support. | [Media methods](https://core.telegram.org/bots/api#sendphoto). |
| Inline mode, deep links, keyboards | Separate query results, callback actions and launch parameters; authorize application actions. | [Features](https://core.telegram.org/bots/features#interactions); keyboards-ui. |
| Groups, channels, permissions, invites and join requests | Model actor/bot/target rights separately; store chat migrations without losing state. | [Chat management](https://core.telegram.org/bots/api#getchatmember). |
| Polls, quizzes, reactions, boosts and checklists | Do not assume every event identifies a user; use the current poll answer identifiers. | [Polls](https://core.telegram.org/bots/api#poll); keyboards-ui. |
| Stickers and custom emoji | Validate sticker type, upload format, set ownership, and allowed custom-emoji usage. | [Stickers](https://core.telegram.org/bots/api#stickers). |
| Location, venues and contacts | Treat shared data as user input; distinguish live-location edits from static messages. | [Location](https://core.telegram.org/bots/api#sendlocation). |
| Payments, gifts, paid media and subscriptions | Separate payment completion, delivery, refund and recurring access; use durable records. | [Stars](https://core.telegram.org/bots/payments-stars); payments-stars. |
| Login widget, Passport and games | Read the particular signature/encryption/score protocol; Mini App auth does not cover these flows. | [Features](https://core.telegram.org/bots/features#integration). |
| Bot profile, localized commands and menu setup | Update only requested scopes; command-menu visibility is not access control. | [BotFather](https://core.telegram.org/bots/features#botfather). |

## Newer contexts requiring explicit routing

### Business / Secretary connections

Read [Business bots](https://core.telegram.org/api/bots/connected-business-bots) and [Business API](https://core.telegram.org/api/business) when acting through an account connection. Persist connection identity, enabled state, granted rights and revocation. Use `business_connection_id` only where the method supports it. Scope jobs and data to that connection; a normal bot-token send is not equivalent to sending on behalf of an account. Gate replies/read/delete/gift/story actions individually and stop queued actions when rights change.

### Managed bots

Read [managed bots](https://core.telegram.org/api/bots/managed-bots). Model manager and managed identities separately, store tokens in a secret store, record token replacement/owner changes, and isolate each bot's updates/configuration. Requests to create/select a managed bot are not blanket permission to operate every connected bot. Design lifecycle recovery for rotated credentials and revoked management.

### Guest mode and bot-to-bot work

Read [guest mode](https://core.telegram.org/api/bots/guest-mode) and the feature guide's [bot-to-bot section](https://core.telegram.org/bots/features#bot-to-bot-communication). A guest invocation supplies bounded context and a scoped reply route, not history access. Keep caller identity distinct from the bot that supplied a request. Prevent message loops, cap delegation depth, validate the external action requested, and keep application authorization outside generated text.

### Topics, communities and channel direct messages

Model topic IDs in addition to chat IDs. A forum topic, private bot topic and channel direct-message topic have distinct APIs and permission requirements; do not substitute `message_thread_id` for every context. Preserve the incoming context when replying. Read [topics](https://core.telegram.org/api/forum) and [feature guide](https://core.telegram.org/bots/features#channel-direct-messages-and-suggested-posts). Communities add membership/linkage events; track them without assuming all linked chats share permissions or user lists.

### Rich, ephemeral and generated messages

Use [rich-messaging](../../telegram-bot-rich-messaging/SKILL.md) for Rich Messages and temporary drafts. Ephemeral responses have their own identity/edit/delete semantics and visibility; ordinary message deletion and editing are not interchangeable. Confirm the API 10.3 parameter shape before adapting older 10.2 examples. Track generation stop updates and scoped draft IDs.

### Stories, suggested posts and paid media

Read [Stories](https://core.telegram.org/api/stories), [suggested posts](https://core.telegram.org/api/suggested-posts) and the relevant Bot API method. Preserve the business/channel context, eligibility, publication state and media constraints. A submitted suggestion, a published item and a payment notification are distinct outcomes. Paid-media previews/access need an application entitlement decision rather than a filename convention.

## When no supplied example covers the feature

1. Read the canonical method/type and the installed SDK source or generated bindings.
2. Confirm required rights, update subscriptions, identity and current feature availability.
3. Prefer an existing SDK method; if absent, adapt a supported raw request path with response/error handling.
4. Add a small application-specific fixture for the new update shape and its permission/duplicate behavior.
5. Record the verified version and any untested live/client behavior. Avoid inventing wrapper names or assuming a new raw field becomes a strongly typed SDK property.
