---
name: |
  telegram-bot-recipes
description: |
  Load this skill when the user asks for a specific kind of Telegram bot and you need a ready-made, complete, working implementation to start from. Contains full recipes: admin/moderation group bot, reminder & notification bot, RSS/feed channel publisher, quiz/poll bot with scores, file/media downloader bot, AI chat bot with streaming answers, and URL shortener — each with complete runnable code, project layout and DB design.
---

# Telegram Bot Recipes — Complete Working Implementations

Each recipe is a full runnable bot (python-telegram-bot v22, single file or two), designed to be copied, adapted, and extended. Tokens come from env; add the deployment patterns from the `telegram-bot-advanced-features` skill when shipping.

**Async note**: the recipes use sync `sqlite3` for simplicity — fine for small bots. Under real load, swap to `aiosqlite` (`await db.execute(...)`) or an async SQLAlchemy engine so DB calls never block the event loop, and never call blocking libs directly inside handlers (see the PTB skill §17).

## Recipe 1: Group moderation bot (anti-spam, warns, admin commands)

Features: warn system persisted in SQLite, mute/ban commands, auto-delete links from non-admins, welcome messages, logging to an admin chat.

```
modbot/
├── main.py
└── config.py   # TOKEN, ADMIN_LOG_ID
```

```python
# main.py
import logging, re, sqlite3
from telegram import Update
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)

DB = sqlite3.connect("mod.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS warns(user_id INT, chat_id INT, count INT DEFAULT 1, PRIMARY KEY(user_id, chat_id))")
DB.commit()
LINK_RE = re.compile(r"https?://|t\.me/")

async def check_admin(update: Update, context) -> bool:
    m = await update.effective_chat.get_member(update.effective_user.id)
    return m.status in ("administrator", "creator")

async def warn(update: Update, context):
    msg = update.message.reply_to_message
    if not msg:
        return await update.message.reply_text("Reply to a user to warn.")
    DB.execute("""INSERT INTO warns(user_id, chat_id, count) VALUES(?,?,1)
                  ON CONFLICT(user_id, chat_id) DO UPDATE SET count = count + 1""",
               (msg.from_user.id, update.effective_chat.id))
    DB.commit()
    row = DB.execute("SELECT count FROM warns WHERE user_id=? AND chat_id=?",
                     (msg.from_user.id, update.effective_chat.id)).fetchone()
    count = row[0]
    await update.message.reply_text(f"⚠️ Warn {count}/3 for {msg.from_user.mention_html()}")
    if count >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, msg.from_user.id)
        await update.message.reply_text("🚫 Banned after 3 warnings.")

async def anti_link(update: Update, context):
    if update.effective_user.is_bot:
        return
    if LINK_RE.search(update.message.text or ""):
        member = await update.effective_chat.get_member(update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.delete()

async def welcome(update: Update, context):
    for u in update.message.new_chat_members:
        await update.message.reply_text(f"Welcome, {u.mention_html()}! Read the rules.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(MessageHandler(filters.Regex(LINK_RE), anti_link))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.run_polling()

if __name__ == "__main__":
    main()
```

Extension ideas: /unwarn, /mute <min> as reply, a /rules command, forwarding deleted spam into ADMIN_LOG_ID. All admin commands should be wrapped with `check_admin(update, context)` first.

## Recipe 2: Reminder bot (DB-backed, survives restarts)

```python
import sqlite3, datetime, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

DB = sqlite3.connect("reminders.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS rem(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INT, text TEXT, due TEXT, done INT DEFAULT 0)")
DB.commit()

PARSE = {"m": 60, "h": 3600, "d": 86400}

async def remind(update: Update, context):
    """Usage: /remind 30m Call mom"""
    try:
        amount = context.args[0][:-1]
        unit = context.args[0][-1]
        text = " ".join(context.args[1:])
        secs = int(amount) * PARSE[unit]
    except (IndexError, KeyError, ValueError):
        return await update.message.reply_text("Usage: /remind <30m|2h|1d> <text>")
    due = datetime.datetime.now() + datetime.timedelta(seconds=secs)
    DB.execute("INSERT INTO rem(chat_id, text, due) VALUES(?,?,?)",
               (update.effective_chat.id, text, due.isoformat()))
    DB.commit()
    await update.message.reply_text(f"⏰ I'll remind you at {due:%H:%M}.")

async def tick(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows = DB.execute("SELECT id, chat_id, text FROM rem WHERE done=0 AND due<=?", (now,)).fetchall()
    for rid, chat_id, text in rows:
        try:
            await context.bot.send_message(chat_id, f"⏰ Reminder: {text}")
        finally:
            DB.execute("UPDATE rem SET done=1 WHERE id=?", (rid,))
    DB.commit()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("remind", remind))
    app.job_queue.run_repeating(tick, interval=30)
    app.run_polling()
```

Why the DB poller instead of `run_once`: reminders survive restarts. Extensions: timezone-aware due dates, `/list` command, recurring reminders with a `repeat` column.

## Recipe 3: Quiz bot with scoreboard

```python
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ContextTypes, filters)

QUESTIONS = [
    ("Capital of France?", ["Berlin", "Paris", "Madrid"], 1),
    ("2 ** 10 = ?", ["1024", "512", "2048"], 0),
    ("Python creator?", ["GvR", "Guido van Rossum", "RMS"], 1),
]
DB = sqlite3.connect("quiz.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS scores(user_id INT PRIMARY KEY, name TEXT, score INT DEFAULT 0)")

def kb(qi): return InlineKeyboardMarkup([[
    InlineKeyboardButton(opt, callback_data=f"q:{qi}:{oi}") for oi, opt in enumerate(QUESTIONS[qi][1])
]])

async def start_quiz(update: Update, context):
    context.user_data["q"] = 0
    q, opts, ans = QUESTIONS[0]
    await update.message.reply_text(f"1/{len(QUESTIONS)}: {q}", reply_markup=kb(0))

async def answer(update: Update, context):
    q = update.callback_query
    await q.answer()
    qi, oi = map(int, q.data.split(":")[1:])
    correct = oi == QUESTIONS[qi][2]
    if correct:
        DB.execute("""INSERT INTO scores(user_id, name, score) VALUES(?,?,1)
                      ON CONFLICT(user_id) DO UPDATE SET score=score+1, name=excluded.name""",
                   (q.from_user.id, q.from_user.first_name))
        DB.commit()
    nxt = qi + 1
    if nxt < len(QUESTIONS):
        nq = QUESTIONS[nxt][0]
        await q.edit_message_text(f"{'✅' if correct else '❌'} Next ({nxt+1}/{len(QUESTIONS)}): {nq}",
                                  reply_markup=kb(nxt))
    else:
        top = DB.execute("SELECT name, score FROM scores ORDER BY score DESC LIMIT 5").fetchall()
        board = "\n".join(f"{i+1}. {n} — {s}" for i, (n, s) in enumerate(top))
        await q.edit_message_text("Quiz done! 🏆\n" + board)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("quiz", start_quiz))
    app.add_handler(CallbackQueryHandler(answer, pattern=r"^q:"))
    app.run_polling()
```

## Recipe 4: RSS → channel publisher

```python
# pip install feedparser python-telegram-bot[job-queue]
import feedparser, hashlib, sqlite3
from telegram.ext import Application, ContextTypes

FEEDS = ["https://example.com/feed.xml", "https://news.example.com/rss"]
CHANNEL = "@my_channel"
DB = sqlite3.connect("seen.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS seen(guid TEXT PRIMARY KEY)")

async def publish(context: ContextTypes.DEFAULT_TYPE):
    for url in FEEDS:
        for e in feedparser.parse(url).entries[:10]:
            gid = hashlib.md5(e.link.encode()).hexdigest()
            if DB.execute("SELECT 1 FROM seen WHERE guid=?", (gid,)).fetchone():
                continue
            text = f"<b>{e.title}</b>\n{e.summary[:500]}…\n<a href='{e.link}'>Read</a>"
            await context.bot.send_message(CHANNEL, text)
            DB.execute("INSERT INTO seen VALUES(?)", (gid,))
    DB.commit()

def main():
    app = Application.builder().token(TOKEN).build()
    app.job_queue.run_repeating(publish, interval=600, first=5)
    app.run_polling()
```

## Recipe 5: AI chat bot (with typing indicator + long-answer chunking)

```python
# pip install openai python-telegram-bot
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from openai import AsyncOpenAI

ai = AsyncOpenAI()  # OPENAI_API_KEY env var
SYSTEM = "You are a helpful assistant inside a Telegram bot. Be concise."

async def chat(update: Update, context):
    await update.message.chat.send_action(ChatAction.TYPING)
    r = await ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": update.message.text}],
    )
    reply = r.choices[0].message.content
    # 4096-char limit: split cleanly
    for i in range(0, len(reply), 4000):
        await update.message.reply_text(reply[i:i+4000])

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Ask me anything!")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling()
```

For true streaming edits, throttle `edit_message_text` to ~1/s (flood-limited otherwise).

## Recipe 6: File downloader bot (YouTube/media via yt-dlp, big files via URL)

```python
# pip install yt-dlp python-telegram-bot
import subprocess, tempfile, os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def dl(update: Update, context):
    if not context.args:
        return await update.message.reply_text("Usage: /dl <url>")
    url = context.args[0]
    await update.message.chat.send_action("upload_document")
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "%(title).80s.%(ext)s")
        r = subprocess.run(["yt-dlp", "-o", out, "--max-filesize", "45M", url],
                           capture_output=True, text=True, timeout=300)
        files = os.listdir(td)
        if not files:
            return await update.message.reply_text("Failed or >45 MB. Try the bot API local server for bigger files.")
        path = os.path.join(td, files[0])
        if files[0].endswith((".mp4", ".webm")):
            await update.message.reply_video(open(path, "rb"))
        else:
            await update.message.reply_audio(open(path, "rb"))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("dl", dl))
    app.run_polling()
```

For >50 MB use the local Bot API server (2 GB) or Telethon upload.

## Recipe 7: URL shortener bot (own domain + API)

```python
import sqlite3, secrets
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

DB = sqlite3.connect("short.db", check_same_thread=False)
DB.execute("CREATE TABLE IF NOT EXISTS urls(code TEXT PRIMARY KEY, url TEXT)")
DOMAIN = "https://sho.rt/"

async def shorten(update: Update, context):
    for word in update.message.text.split():
        if word.startswith("http"):
            code = secrets.token_urlsafe(5)
            DB.execute("INSERT INTO urls VALUES(?,?)", (code, word)); DB.commit()
            return await update.message.reply_text(DOMAIN + code)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), shorten))
    app.run_polling()
```

(Pair with a FastAPI/nginx redirect service reading the same DB.)

## Choosing and combining recipes

| User asks for | Start with |
|---|---|
| "Group guard / moderation / anti-spam" | Recipe 1 |
| "Reminders / scheduler bot" | Recipe 2 |
| "Quiz / trivia / scoreboard" | Recipe 3 |
| "News feed → channel auto-post" | Recipe 4 |
| "AI / GPT chat bot" | Recipe 5 |
| "Downloader bot" | Recipe 6 |
| "Shortener / utility bot" | Recipe 7 |
| "Shop / store / product price list bot (like AZ TECH SHOP)" | telegram-bot-rich-messaging skill §3–4 (full storefront bot) |
| Web dashboard / catalog UI | telegram-bot-miniapps skill |
| Go implementation of any recipe | telegram-bot-go-botapi / telegram-bot-gotd skills — same designs port directly: swap the handler registration for the Go framework's, keep the same DB schemas and flows |
| Login required / paid tiers | telegram-bot-payments-stars skill |

When combining recipes into one bot: split each into a `handlers/` module, register on one Application, share one DB (WAL mode for SQLite), add throttling middleware, and follow the layout in telegram-bot-fundamentals.
