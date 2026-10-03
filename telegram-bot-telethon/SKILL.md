---
name: |
  telegram-bot-telethon
description: |
  Load this skill for MTProto development with Telethon v1 — userbots, bot accounts over MTProto, events (NewMessage, CallbackQuery, InlineQuery, Album), client methods, downloading/uploading files up to 2-4 GB, raw API calls, admin/userbot automation, and Telethon-specific patterns with complete examples.
---

# Telethon v1 — Complete MTProto Build Guide

## 1. What Telethon is and when to use it

Telethon is an **asyncio Python 3 MTProto library** to talk to Telegram's servers directly — as a **user account (userbot)** or a **bot account**. Unlike the HTTP Bot API: no polling, no webhooks, full access to nearly the whole Telegram API (messages, channels, users, files, stories...), files up to **2 GB (4 GB with Premium)**, and the ability to act as a real user.

Use Telethon when the bot must: read group messages without BotFather privacy constraints (as a user), scrape/export history, manage channels as an admin user, upload/download large files, use features not in the Bot API, or run automation on your own account. For ordinary bot features, PTB/aiogram over HTTP is simpler.

Status: v1 (1.45) is in maintenance mode; the repo lives at https://codeberg.org/Lonami/Telethon; docs at https://docs.telethon.dev; raw API reference at https://tl.telethon.dev. Telethon v2 is a separate alpha with breaking changes — unless requested, write v1 code.

## 2. Setup

```bash
pip install telethon
# fast (optional, recommended): pip install cryptg
```

Get `api_id`/`api_hash` from https://my.telegram.org → API Development. For a **bot account**, also get the token from @BotFather.

Login (both flows look the same — pass what you have):

```python
from telethon import TelegramClient

api_id = 12345
api_hash = "0123456789abcdef0123456789abcdef"

# User login (interactive, one time — session is saved to 'myaccount.session')
client = TelegramClient("myaccount", api_id, api_hash)

async def main():
    await client.start()               # asks phone → code → 2FA password if needed
    me = await client.get_me()
    print("Logged in as", me.first_name)

with client:
    client.loop.run_until_complete(main())

# Bot login — just pass bot_token, no interactive prompts
client = TelegramClient("mybot", api_id, api_hash)
await client.start(bot_token="123456:AAE...")
```

Sessions: `StringSession` for serverless/containers:

```python
from telethon.sessions import StringSession
client = TelegramClient(StringSession(), api_id, api_hash)
await client.start()
print(StringSession.save(client))   # print once, store in env var
client = TelegramClient(StringSession(os.environ["TG_SESSION"]), api_id, api_hash)
```

Never commit `.session` files or session strings — they grant full account access.

## 3. Client methods — the friendly API

```python
me = await client.get_me()
dialogs = [d async for d in client.iter_dialogs()]           # all chats/channels/groups
msgs = await client.get_messages("username", limit=50)        # newest first
async for m in client.iter_messages(chat, limit=1000): ...    # iterate history

msg = await client.send_message("username", "Hello!")         # user/phone/id/PeerInput
await client.send_file("username", "photo.jpg", caption="Pic")
await client.send_file(chat, ["a.jpg", "b.jpg"])             # album
await msg.reply("Replying")
await msg.edit("Edited text")
await msg.delete(revoke=False)
await msg.forward_to("target_chat")
await msg.download_media("downloads/")                       # media → file
await client.download_profile_photo("username", "photo.jpg")

entity = await client.get_entity("username")                 # resolves to User/Chat/Channel
full = await client.get_entity(await client.get_input_entity(-1001234567890))

await client.pin_message(chat, msg_id, notify=False)
await client.edit_message(chat, msg_id, "new text")
await client.delete_messages(chat, [1, 2, 3])

# Admin / channel
await client.edit_admin(chat, user, change_info=True, delete_messages=True, ban_users=True)
await client.edit_permissions(chat, send_messages=False)      # mute all
await client.ban_participant(chat, user)
await client.kick_participant(chat, user)
await client.join_chat("https://t.me/joinchat/xxx")
await client.leave_chat(chat)

# Account
await client.edit_profile(bio="I am a bot")
await client.update_profile(first_name="NewName")

# Inline query to another bot
results = await client.inline_query("like", "Do you like Telethon?")
await results[0].click("target_chat")

# Get channel/megagroup stats (requires admin)
stats = await client.get_stats(channel_id)
```

Entities resolve by: username (`@name` / `name`), phone (`+1555...`), raw ID (must have seen the chat before, use `int`; for channels `-100...`), or `t.me` invite links (as input entities).

## 4. Events — handlers

```python
from telethon import TelegramClient, events

client = TelegramClient("mybot", api_id, api_hash)

@client.on(events.NewMessage(pattern=r"^/start$", incoming=True))
async def start(event):
    await event.reply("Hello!")

@client.on(events.NewMessage(chats=["mygroup"], func=lambda e: e.photo))
async def photos(event):
    await event.download_media()
    await event.reply("Saved your photo")

# Reply keyboard + callback (bot accounts and user chats with bots)
from telethon import Button

@client.on(events.NewMessage(pattern="/menu"))
async def menu(event):
    await event.reply("Choose:", buttons=[
        [Button.inline("Tap me", b"action:tap"), Button.url("Site", "https://example.com")],
        [Button.text("Help"), Button.text("Cancel")],
    ])

@client.on(events.CallbackQuery(data=re.compile(rb"^action:"))
async def on_tap(event):
    await event.answer("Tapped!")       # always answer to stop the spinner
    await event.edit("You tapped: " + event.data.decode())

client.add_event_handler(handler_func, events.NewMessage(...))  # programmatic form
client.run_until_disconnected()
```

Event types:

- `events.NewMessage` — filters: `chats=`, `from_users=`, `pattern=` (regex on text), `incoming=`/`outgoing=`, `func=`, `private=True`, `group=True`
- `events.MessageEdited`, `events.MessageDeleted`, `events.MessageRead`
- `events.Album` — media groups arrive together (`event.messages`)
- `events.ChatAction` — joins, leaves, title/photo changes, new members
- `events.UserUpdate` — typing, online status
- `events.CallbackQuery` — inline button taps (with `data=` regex filter)
- `events.InlineQuery` / `events.ChosenInlineResult`
- `events.Raw` — any raw MTProto update (`events.Raw(types.UpdateChannel...))`)
- `events.Edited`, `events.ChannelCreated`, `events.UserAdded`

Useful event properties: `event.chat_id`, `event.sender_id`, `event.text`, `event.raw_text`, `event.message` (Message object with `.media`, `.file`, `.buttons`, `.date`, `.reply_to_msg_id`), `event.is_private`, `event.is_group`, `event.respond()`, `event.answer()` (in groups vs reply).

Important: in groups, userbots see ALL messages; bot accounts on MTProto still follow bot privacy rules (unless privacy is off via BotFather or the bot is admin).

## 5. Buttons (reply markup) — Telethon's own Button class

```python
from telethon.tl.custom import Button   # or from telethon import Button

await client.send_message(chat, "Options", buttons=[
    [Button.inline("Callback", b"cb:1")],
    [Button.text("Reply keyboard A", "B")],   # full-width rows
    [Button.request_contact("Share contact")],
    [Button.request_location("Share location")],
    [Button.request_poll("Send poll")],
    [Button.url("Open site", "https://example.com")],
    [Button.switch_inline("Use inline", query="hi", same_peer=False)],
])

# clear the reply keyboard:
await client.send_message(chat, "Bye", buttons=Button.clear())
# force reply:
await client.send_message(chat, "?", buttons=Button.force_reply())
```

## 6. Media handling — the big-file advantage

```python
# Download with progress
def progress(current, total):
    print(f"{current} / {total} bytes ({current/total:.1%})")

await client.download_media(message, "file.zip", progress_callback=progress)

# Upload and send with attributes
from telethon.tl.types import DocumentAttributeVideo
await client.send_file(chat, "video.mp4",
    caption="My video",
    supports_streaming=True,
    attributes=[DocumentAttributeVideo(duration=60, w=1920, h=1080)],
    thumb="thumb.jpg",
)
# send as album with captions per-item
await client.send_file(chat, [f1, f2], caption=["First", "Second"])

# Download media of a whole channel
async for msg in client.iter_messages(channel, limit=1000):
    if msg.photo or msg.video:
        await msg.download_media("downloads/")
```

## 7. Raw API — the full power

Anything without a friendly wrapper is a raw request; find names at https://tl.telethon.dev:

```python
from telethon.tl import functions, types

result = await client(functions.messages.GetHistoryRequest(
    peer="username",
    limit=100,
))
for m in result.messages: ...

# Create a channel
r = await client(functions.channels.CreateChannelRequest(
    title="My Channel", about="Description", megagroup=True,
))

# Set a reaction on a message
await client(functions.messages.SendReactionRequest(
    peer=chat, msg_id=msg.id,
    reaction=[types.ReactionEmoji(reaction="🔥")],
))

# Get all chats the account can see
chats = await client(functions.messages.GetAllChatsRequest(except_ids=[]))
```

Rule of thumb: check the friendly method first (`client.<method>`); fall back to `client(functions.*.Request(...))`.

## 8. Working as a bot account over MTProto

```python
client = TelegramClient("bot", api_id, api_hash)
await client.start(bot_token=TOKEN)
# Commands menu:
await client(functions.bots.SetBotCommandsRequest(
    scope=types.BotCommandScopeDefault(), lang_code="en",
    commands=[types.BotCommand(command="start", description="Start")],
))
```

Bot accounts on MTProto receive updates identically; the advantage over HTTP is no webhook/polling and direct protocol — useful on networks where HTTP Bot API is slow or blocked.

## 9. Conversations — step-by-step chats with a bot or user

```python
from telethon import events

@client.on(events.NewMessage(pattern="^/ask$"))
async def ask(event):
    chat = await event.get_chat()
    async with client.conversation(chat) as conv:
        await conv.send_message("What's your name?")
        name = (await conv.get_response()).text
        await conv.send_message(f"Hello, {name}!")
```

Caveats (from the docs): Conversation API has no persistence, interacts poorly with other event handlers, and is meant for simple cases — for complex flows keep state yourself (a `dict` keyed by `chat_id` or a DB).

## 10. Multi-account / parallel clients

```python
clients = [TelegramClient(f"acc{i}", api_id, api_hash) for i in range(3)]
await asyncio.gather(*(c.start() for c in clients))
# then run each client's handlers concurrently:
await asyncio.gather(*(c.run_until_disconnected() for c in clients))
```

Use cases: forwarding across accounts, high-volume scraping with rotation, separating user and bot accounts.

## 11. Common userbot automation examples

```python
# Auto-delete links in a group you admin
@client.on(events.NewMessage(chats="mygroup", pattern=r"https?://"))
async def anti_link(event):
    if await event.chat.get_permissions(event.sender_id).is_admin is False:
        await event.delete()

# Welcome new members
@client.on(events.ChatAction())
async def welcome(event):
    if event.user_joined:
        await event.reply(f"Welcome, {await event.get_user().first_name}!")

# Keep alive a background job
async def hourly_broadcast():
    while True:
        await client.send_message("mychannel", "Hourly ping")
        await asyncio.sleep(3600)
client.loop.create_task(hourly_broadcast())
```

## 12. Errors and safety

```python
from telethon import errors
try:
    await client.send_message(user, "hi")
except errors.FloodWaitError as e:
    await asyncio.sleep(e.seconds)      # mandatory wait; the ban risk is real
except errors.rpcerrorlist.UserIsBlockedError:
    ...
except errors.SessionPasswordNeededError:
    ...
```

Rules:
- Respect `FloodWaitError` — sleeping for the given seconds is mandatory; ignoring it risks account bans.
- Userbot abuse (mass DMs, spam, scraping private data) violates Telegram ToS and gets accounts banned. Only build automation for accounts the user owns, on chats they administer or have permission in.
- Reuse one client; creating many connections per token/phone triggers limits.
- `client.run_until_disconnected()` must run inside the asyncio loop; in scripts, `with client:` + `client.loop.run_until_complete(...)`.

## 13. Pre-ship checklist

- [ ] api_id/api_hash/session in env vars; `.session` files gitignored
- [ ] `event.answer()` called for every CallbackQuery
- [ ] FloodWait handling on all mass-send loops
- [ ] Event filters scoped (`chats=`, `incoming=`) to avoid accidental global triggers
- [ ] For bots: commands registered; privacy mode considered
- [ ] Long-running tasks use `client.loop.create_task`, not blocking calls
- [ ] Tested with a burner account if doing userbot automation
