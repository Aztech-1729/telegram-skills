# Telethon 1.45.0 implementation guide

This guide is original application guidance, not a complete protocol manual. The Python fragments below are **application patterns**: they assume an authenticated `client`, valid authorized peers, and surrounding async lifecycle. The separately linked [starter](../assets/starter/bot.py) is a complete executable script.

## Authentication, sessions, and lifecycle

Install `Telethon==1.45.0`; optional `cryptg` accelerates encryption when a compatible build is available. Telethon uses MTProto for both user and bot accounts, so supply `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org). A bot additionally needs `BOT_TOKEN`. Never assume a token removes the API credential requirement. Prefer PTB or aiogram for ordinary Bot API command bots; use Telethon when an existing project or required MTProto method justifies it.

For an interactive **user** application, create `TelegramClient(session_path, api_id, api_hash)` inside an async entrypoint and `await client.start()`. The first authorization may ask for phone, code, and 2FA password. For a **bot**, use `await client.start(bot_token=token)`. An existing authorized session is reused: check `await client.get_me()`, account type, and expected identity before handlers or background work can act. Do not put login codes/passwords in source or logs.

Default SQLite sessions retain authorization and entity information. Use a persistent, access-controlled volume and exclude `*.session`, `*.session-journal`, exported session strings, and secret files from version control. Do not run two independent writers against the same SQLite session. One session per intentional account/client avoids identity and locking surprises. `StringSession(saved_value)` can restore authorization, but a fresh `StringSession()` does not magically authenticate and exporting it discloses a credential. Store strings in a secret manager and revoke compromised sessions through Telegram.

Create a client, register handlers, authenticate, then `await client.run_until_disconnected()` in one loop; always `await client.disconnect()` in `finally`. In an async web application, await Telethon methods directly and integrate startup/shutdown with the host lifecycle. `telethon.sync` helpers and nested `asyncio.run()` are unsuitable inside an already running loop. Keep strong references to supervised background tasks, cancel and await them on shutdown, and observe failures. No polling/webhook server is required for MTProto's update connection; network reachability, update handling, and reconnect supervision still matter.

The starter accepts `API_ID`, `API_HASH`, `BOT_TOKEN`, optional `TG_SESSION` (secret string), or `TG_SESSION_FILE` (default `mtproto-bot`). It verifies the bot ID embedded in the token against the authorized session.

## Events, filters, and dispatch

Use registered event builders, not assumed names. Supported builders include `NewMessage`, `MessageEdited`, `MessageDeleted`, `MessageRead`, `Album`, `ChatAction`, `UserUpdate`, `CallbackQuery`, `InlineQuery`, and `Raw`. There are no v1 builders named `ChosenInlineResult`, `Edited`, `ChannelCreated`, or `UserAdded`. Use an appropriate `ChatAction` flag or supported raw update after checking the layer type.

`NewMessage` supports `chats`, `from_users`, `incoming`/`outgoing`, `forwards`, `pattern`, and `func`. For a group use `func=lambda e: e.is_group`; for a private command:

```python
from telethon import events

@client.on(events.NewMessage(
    incoming=True,
    pattern=r'^/start(?:@\w+)?$',
    func=lambda e: e.is_private,
))
async def start(event):
    await event.respond('Hello', parse_mode=None)
    raise events.StopPropagation
```

Choose registration order intentionally: multiple handlers can match the same update; `StopPropagation` prevents subsequent handlers. Handle edits separately from new messages, avoid echoing your own outgoing messages, and scope automation to configured chats. Regex patterns match at the start; use a deliberate search predicate if detecting links anywhere in text. Media groups deserve `events.Album` with `event.messages`, rather than duplicating actions for every constituent message.

`event.chat_id` and `sender_id` may be unavailable for some updates. Cached `event.chat`/`sender` may be absent; use `await event.get_chat()` or `await event.get_sender()` when required. `NewMessage` provides `respond`/`reply`; `answer` is for callback/inline query events, not a generic alternative to replying. Deleted-message updates may lack enough peer information to reconstruct a conversation. Bot privacy and actual membership limit visible messages; a user session sees only messages its account can access.

## Buttons, callback ownership, and inline queries

Inline markup: `Button.inline(text, data=bytes)`, `Button.url(text, url)`, `Button.switch_inline(text, query=..., same_peer=...)`. Reply markup: `Button.text(text)`, `Button.request_phone(text)`, `Button.request_location(text)`, `Button.request_poll(text)`. Phone/location prompts apply to eligible private chats. Never mix the families in a single message. `Button.text('A', 'B')` does not create two buttons: use a two-element row.

```python
from telethon import Button

await client.send_message(
    chat, 'Actions',
    buttons=[[Button.inline('Close', b'menu:close'), Button.url('Help', 'https://telegram.org')]],
)
await client.send_message(
    private_chat, 'Contact options',
    buttons=[[Button.request_phone('Share phone')], [Button.text('Cancel')]],
)
await client.send_message(private_chat, 'Done', buttons=Button.clear())
```

Callback data has a 64-byte maximum; count UTF-8 bytes, not characters. Store large/sensitive state server-side with an opaque expiring identifier. Match `events.CallbackQuery(data=...)` with exact bytes or a bytes regex; decode defensively and recheck actor, message/session ownership, and current permissions. Call `event.answer()` promptly, then perform bounded work and `event.edit(...)` if editable. Handle stale callbacks and `MessageNotModifiedError`. Inline-mode callbacks may lack a normal chat message; use the callback's edit helpers instead of assuming `event.message` exists.

For `events.InlineQuery`, use `event.builder.article(title, text=..., parse_mode=None)` and `await event.answer(results, cache_time=..., private=...)`; enable inline mode in BotFather first. Tailor cache policy to per-user data and avoid leaking personalized results. A user client querying another bot can use `await client.inline_query(bot, query)` and click a chosen result in an authorized destination; this is different from hosting an inline bot.

## Entities, messages, and history

Use `get_input_entity` for a request-ready peer and `get_entity` when full entity information is needed. Usernames, known IDs, cached peers, and full objects are not interchangeable without resolution. Access hashes are account-specific; an arbitrary integer or invite link is not universal authorization. Resolve private invites explicitly rather than expecting `get_input_entity` to join.

Friendly methods cover `send_message`, `send_file`, `edit_message`, `delete_messages`, `pin_message`, `forward_messages`, `iter_dialogs`, and `iter_messages`. Message objects expose `reply`, `edit`, `delete`, `forward_to`, and `download_media`. Prefer iterators and bounded limits over loading an entire history into memory. History availability depends on account type, membership, rights, and method eligibility; MTProto bot accounts cannot use every history request.

Export only the requested authorized scope. Persist a peer/message checkpoint, use overlapping pages plus deduplication for restart recovery, and handle removed/private chats. Chat IDs and usernames can change; usernames are not durable database keys. Escape user text for HTML, or use `parse_mode=None` for literal echoes. Edits/deletes may fail for permissions, age, or missing messages; do not claim all message methods work for every account.

## Media and transfer limits

`send_file` accepts supported paths, bytes, file-like streams, existing media, and supported remote URLs; select the input type deliberately. File-like objects should have a meaningful `name` for type inference and remain open during upload. `download_media` can save to a controlled destination or return bytes with `file=bytes`; bound memory use and treat downloaded names/content as untrusted. Do not accept arbitrary filesystem paths or URLs from users without an application policy.

An album uses a list of files, with per-item captions where needed. Validate media type/count, actual video dimensions and duration, thumbnail requirements, and availability of local files; invented metadata is not a transcoder. For `DocumentAttributeVideo`, set actual `duration`, `w`, `h`; `supports_streaming=True` does not make incompatible media streamable.

`progress_callback(current, total)` should tolerate zero/unknown totals and update UI sparingly. Cancel supervised transfer tasks cleanly; persisted download checkpoints are separate from the account session. Telegram's [file protocol](https://core.telegram.org/api/files) uses account/server configuration to determine allowed parts and size. Do not promise every account, bot, upload path, or download can handle a fixed '2–4 GB' limit. Optional `cryptg` may improve CPU-heavy transfers; measure bottlenecks before adding connections.

## Raw requests and moderation

Prefer a friendly wrapper when available. Generated classes under `telethon.tl.functions` are layer-specific; inspect their constructors, fill required parameters, and check Telegram's account eligibility for the method. A wrapper's existence does not grant permission.

For an authorized **user** history request (all fields supplied):

```python
from telethon.tl import functions

peer = await client.get_input_entity(chat)
history = await client(functions.messages.GetHistoryRequest(
    peer=peer, offset_id=0, offset_date=None, add_offset=0,
    limit=100, max_id=0, min_id=0, hash=0,
))
```

For user-only joins/profile operations use `functions.channels.JoinChannelRequest(channel)`, `functions.messages.ImportChatInviteRequest(hash=invite_hash)`, and `functions.account.UpdateProfileRequest(first_name=..., about=...)`. Parse the hash from a supported invite link and handle expired links, join requests, or membership restrictions. There are no friendly `join_chat`, `leave_chat`, `edit_profile`, or `update_profile` methods in this baseline. Leave an authorized chat using `delete_dialog(chat)`; enumerate dialogs with `iter_dialogs`, not nonexistent `messages.GetAllChatsRequest`.

Use `edit_admin` to grant supported rights and `edit_permissions` for restrictions. In `edit_permissions`, `False` denies the named permission; `view_messages=False` bans a participant where supported. `kick_participant` performs a ban/unban style kick and is not a permanent ban. `ban_participant` does not exist. Verify chat kind, your admin rights, target immunity, intended scope, and expiry before mutation. A group default restriction is distinct from restricting a specified user.

Permission checks require correct await precedence:

```python
permissions = await client.get_permissions(chat, sender)
if not permissions.is_admin and not permissions.is_creator:
    # Apply only the explicitly authorized moderation policy here.
    pass
```

For member welcomes, await `user = await event.get_user()` before reading attributes; use `event.user_joined`/`user_added` and handle absent users. Stats require eligible channels and rights; `get_stats` is not available for arbitrary private chats. Channel creation, reactions, stories, and business features use their current generated requests and account restrictions; inspect the pinned layer rather than assuming full API coverage. For bot commands use `functions.bots.SetBotCommandsRequest(scope=types.BotCommandScopeDefault(), lang_code='', commands=[...])`.

## Conversations, state, scheduling, and multiple clients

`client.conversation(peer, timeout=..., total_timeout=..., max_messages=...)` can coordinate a small transient exchange with one peer. Timeouts are seconds. Its API has no persistence and can interact poorly with event handlers; an exclusive conversation also prevents another exclusive one in the same chat. Handle timeout/cancellation and validate every response. It is especially unsuitable for a multi-user group questionnaire keyed only by chat.

Complex flows need explicit state keyed by account, chat, and sender (and thread/flow when applicable), cancellation, expiry, durable storage, and serialization per flow. An in-memory dictionary disappears on restart; a database without locking does not prevent concurrent transitions. Do not hold a global sequential update handler open while waiting for a future response, as the response must itself be dispatched.

For periodic work use a supervised async task or a scheduler with an explicit version and timezone. `asyncio.sleep(3600)` means seconds and drifts with work duration; it does not survive restarts. Durable scheduled sends need a persisted intended time, job ID, deduplication, missed-run policy, and cancellation. Do not call unobserved `create_task` and assume delivery is guaranteed.

Multiple clients can coexist in one loop with distinct sessions and `asyncio.gather`; start each with its own intended credentials and verify each identity. Cancel peers and disconnect all clients if startup or a critical task fails. Use this for deliberate account separation, not high-volume account rotation or flood-limit avoidance.

## Errors, retries, and performance

Catch the expected `telethon.errors` classes at the operation boundary. `FloodWaitError.seconds` provides the requested delay; wait within an explicit task budget or defer a durable job until that time. The client can automatically sleep for short waits up to `flood_sleep_threshold` (default 60 seconds). Configure this alongside finite `request_retries`, `connection_retries`, `retry_delay`, timeouts, and a cancellation/shutdown budget. Setting an infinite retry count can stall a job indefinitely.

Authorization failures require fixing/revoking the relevant session, not repeated login attempts; 2FA challenges belong to the login flow. Permission, invalid-peer, blocked-user, expired-reference, and unknown RPC errors are distinct from transient transport failures. Log error class and operation context without tokens, hashes, session strings, login codes, or unnecessary message content. Do not catch all failures and silently claim success. After an ambiguous timeout, reconcile the intended mutation before replaying it; external effects require application idempotency.

By default, updates may run concurrently. `sequential_updates=True` preserves dispatch order but its pending queue is unbounded, so handlers must stay short. Serialize stateful work per key and bound expensive workers; do not use global sequential processing as an excuse for slow blocking operations. Use async I/O or move blocking work to a thread/process, keep one reusable client, and paginate exports.

Structure real applications around configuration, client lifecycle, scoped event modules, domain services, and storage. Test authorization/input validation and state transitions offline with fakes; test real permissions, reconnects, media, flood waits, and update delivery only with an authorized controlled account. See [validation](validation.md) for exactly what was checked here.

