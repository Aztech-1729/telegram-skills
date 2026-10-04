# Telegram capability routing and integration decisions

Checked **2026-10-04**, against the Telegram feature guide, Bot API 10.3 reference, and topic guides. This map covers feature families relevant to application design; consult the linked reference for the full method/schema inventory. Links under `/api/` describe native MTProto; use the HTTP Bot API types/methods below when implementing a bot-token application.

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

Start with HTTP [BusinessConnection](https://core.telegram.org/bots/api#businessconnection), [BusinessBotRights](https://core.telegram.org/bots/api#businessbotrights) and [getBusinessConnection](https://core.telegram.org/bots/api#getbusinessconnection). Handle connection plus business-message/edit/delete updates. Persist connection identity, enabled state, granted rights and revocation; fetch an unknown connection after restart before acting. Reply permission has a recent-incoming-message condition in eligible private chats, so an old queued reply must be revalidated at dispatch. Use `business_connection_id` only where the method supports it. Scope jobs and data to that connection; a normal bot-token send is not equivalent to sending on behalf of an account. Gate replies/read/delete/gift/story actions individually and stop queued actions when rights change. Read [native connected bots](https://core.telegram.org/api/bots/connected-business-bots) for MTProto datacenter/connection wrapping.

### Managed bots

Use the [Bot API managed-bot flow](https://core.telegram.org/bots/features#managed-bots): enable manager capability in BotFather, present the creation request/deep link, handle `managed_bot`, then use `getManagedBotToken` for the granted managed identity. `replaceManagedBotToken` rotates credentials; access-settings methods manage the documented restrictions. Creation is confirmed by the user; do not invent a bot-token `createBot` method. The [native guide](https://core.telegram.org/api/bots/managed-bots) explains user-only MTProto creation. Model manager and managed identities separately, store tokens in a secret store, record token replacement/owner changes, and isolate each bot's updates/configuration. Requests to create/select a managed bot are not blanket permission to operate every connected bot. Design lifecycle recovery for rotated credentials and revoked management.

### Guest mode and bot-to-bot work

For HTTP guest mode, handle `Update.guest_message` and answer its `Message.guest_query_id` through [answerGuestQuery](https://core.telegram.org/bots/api#answerguestquery); the [native guest guide](https://core.telegram.org/api/bots/guest-mode) uses a different update/result path. A guest invocation supplies bounded context and a scoped reply route, not history access. Keep caller user/chat identity separate from the message author. The [bot-to-bot guide](https://core.telegram.org/bots/features#bot-to-bot-communication) has different enablement rules for groups, private bot usernames and business-account chats; private bot-to-bot sending requires both bots to enable the capability. Prevent message loops, cap delegation depth, validate the external action requested, and keep application authorization outside generated text.

### Topics, communities and channel direct messages

Model topic IDs in addition to chat IDs. A forum topic, private bot topic and channel direct-message topic have distinct APIs and permission requirements; do not substitute `message_thread_id` for every context. Preserve the incoming context when replying. Read [topics](https://core.telegram.org/api/forum) and [feature guide](https://core.telegram.org/bots/features#channel-direct-messages-and-suggested-posts). Communities add membership/linkage events; track them without assuming all linked chats share permissions or user lists.

Store forum/private bot threads as `message_thread_id`; channel direct-message destinations use `direct_messages_topic_id` on supported sends. Preserve `business_connection_id` separately. A callback may reference an inaccessible message or an inline message without a chat ID; do not manufacture ordinary reply context from missing fields. Community-linked chat joins are service messages within `Update.message`; they are not a new universal membership permission.

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
