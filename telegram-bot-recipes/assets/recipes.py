"""Seven selectable PTB recipe starters; optional dependencies load by mode."""
import argparse
import asyncio
import hashlib
import logging
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import urlsplit

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from recipe_store import Store, deliver_due, public_url

QUESTIONS = [("Capital of France?", ["Berlin", "Paris", "Madrid"], 1),
             ("2 ** 10?", ["1024", "512", "2048"], 0)]
LINKS = re.compile(r"https?://|t\.me/", re.I)
LOG = logging.getLogger(__name__)


async def authorized(bot, chat, user):
    member = await bot.get_chat_member(chat, user)
    return member.status in {"creator", "administrator"}


async def warn(update, context):
    msg, user = update.effective_message, update.effective_user
    if msg is None or user is None or update.effective_chat.type not in {"group", "supergroup"}:
        return
    if not await authorized(context.bot, msg.chat_id, user.id):
        await msg.reply_text("Only group administrators can warn users.")
        return
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if target is None or await authorized(context.bot, msg.chat_id, target.id):
        await msg.reply_text("Reply to a non-administrator user's message.")
        return
    me = await context.bot.get_chat_member(msg.chat_id, context.bot.id)
    if not getattr(me, "can_restrict_members", False):
        await msg.reply_text("I need administrator rights to restrict members.")
        return
    count = await asyncio.to_thread(context.bot_data["store"].warn, msg.chat_id, target.id)
    if count >= 3:
        await context.bot.ban_chat_member(msg.chat_id, target.id)
    await msg.reply_text(f"Warning {count}/3 for {target.first_name}." + (" User banned." if count >= 3 else ""))


async def anti_link(update, context):
    msg, user = update.effective_message, update.effective_user
    if msg is None or user is None or user.is_bot or not LINKS.search(msg.text or ""):
        return
    if await authorized(context.bot, msg.chat_id, user.id):
        return
    me = await context.bot.get_chat_member(msg.chat_id, context.bot.id)
    if getattr(me, "can_delete_messages", False):
        await msg.delete()


async def remind(update, context):
    msg = update.effective_message
    try:
        match = re.fullmatch(r"([1-9][0-9]{0,5})([mhd])", context.args[0])
        if not match:
            raise ValueError()
        seconds = int(match[1]) * {"m": 60, "h": 3600, "d": 86400}[match[2]]
        text = " ".join(context.args[1:])
        if not text or len(text) > 3000 or seconds > 365*86400:
            raise ValueError()
    except (IndexError, ValueError):
        await msg.reply_text("Usage: /remind <30m|2h|1d> <text>; maximum one year.")
        return
    due = int(time.time()) + seconds
    await asyncio.to_thread(context.bot_data["store"].remind, msg.chat_id, text, due)
    await msg.reply_text("Reminder saved.")


async def tick(context):
    await deliver_due(context.bot_data["store"], context.bot.send_message, int(time.time()))


def quiz_markup(quiz_id, step):
    return InlineKeyboardMarkup([[InlineKeyboardButton(option, callback_data=f"q:{quiz_id}:{step}:{i}")]
                                 for i, option in enumerate(QUESTIONS[step][1])])


async def quiz(update, context):
    msg, user = update.effective_message, update.effective_user
    quiz_id = await asyncio.to_thread(context.bot_data["store"].new_quiz, user.id, msg.chat_id)
    await msg.reply_text(QUESTIONS[0][0], reply_markup=quiz_markup(quiz_id, 0))


async def answer(update, context):
    query = update.callback_query
    await query.answer()
    if query.message is None:
        return
    try:
        _, quiz_id, step, choice = query.data.split(":")
        step, choice = int(step), int(choice)
        correct = await asyncio.to_thread(context.bot_data["store"].answer, quiz_id,
                                         query.from_user.id, query.message.chat.id, step, choice, QUESTIONS)
    except (ValueError, TypeError):
        await context.bot.send_message(query.from_user.id, "This answer is invalid, expired, or already submitted.")
        return
    next_step = step + 1
    prefix = "Correct. " if correct else "Incorrect. "
    if next_step < len(QUESTIONS):
        await query.edit_message_text(prefix + QUESTIONS[next_step][0], reply_markup=quiz_markup(quiz_id, next_step))
    else:
        await query.edit_message_text(prefix + "Quiz complete. Your score is stored.")


async def publish(context):
    import feedparser
    import httpx
    store = context.bot_data["store"]
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for feed in context.bot_data["feeds"]:
            # Feeds are operator configuration, never supplied by chat users.
            async with client.stream("GET", feed) as response:
                response.raise_for_status()
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise ValueError("Feed exceeds configured size limit")
            parsed = await asyncio.to_thread(feedparser.parse, bytes(data))
            for item in reversed(parsed.entries[:10]):
                link = item.get("link", "")
                try:
                    public_url(link)
                except ValueError:
                    continue
                guid = hashlib.sha256(str(item.get("id", link)).encode()).hexdigest()
                if await asyncio.to_thread(store.seen, feed, guid):
                    continue
                await context.bot.send_message(context.bot_data["channel"], str(item.get("title", "Article"))[:500] + "\n" + link)
                await asyncio.to_thread(store.mark_seen, feed, guid)


async def ai_chat(update, context):
    from openai import AsyncOpenAI
    msg = update.effective_message
    if len(msg.text) > 8000:
        await msg.reply_text("Please send a shorter question.")
        return
    await context.bot.send_chat_action(msg.chat_id, "typing")
    async with AsyncOpenAI(timeout=45, max_retries=1) as client:
        response = await client.responses.create(model=context.bot_data["model"],
                    instructions="Answer concisely in plain text for a Telegram chat.",
                    input=msg.text, max_output_tokens=1600, store=False)
    text = response.output_text or "No text answer was returned."
    # Split by UTF-16 units so astral characters do not exceed Telegram's bound.
    parts, part, units = [], "", 0
    for char in text:
        width = 2 if ord(char) > 0xFFFF else 1
        if units + width > 4000:
            parts.append(part)
            part, units = "", 0
        part += char
        units += width
    parts.append(part)
    for part in parts:
        await msg.reply_text(part)


async def download(update, context):
    msg = update.effective_message
    try:
        url = public_url(context.args[0])
        if urlsplit(url).hostname.lower() not in context.bot_data["download_hosts"]:
            raise ValueError()
    except (IndexError, ValueError):
        await msg.reply_text("Usage: /dl <HTTP(S) URL from an operator-approved host>")
        return
    async with context.bot_data["download_limit"]:
        with tempfile.TemporaryDirectory() as directory:
            process = await asyncio.create_subprocess_exec(sys.executable, "-m", "yt_dlp",
                "--ignore-config", "--no-plugin-dirs", "--no-playlist", "--max-downloads", "1",
                "--max-filesize", "45M", "--socket-timeout", "15", "--retries", "1",
                "--format", "best[filesize<45M]/best", "--output", str(Path(directory)/"media.%(ext)s"),
                "--", url, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            try:
                await asyncio.wait_for(process.wait(), timeout=180)
            except (TimeoutError, asyncio.CancelledError):
                process.kill()
                await process.wait()
                raise
            files = [p for p in Path(directory).iterdir() if p.is_file() and p.suffix not in {".part", ".ytdl"}]
            if len(files) != 1 or files[0].stat().st_size > 45_000_000:
                await msg.reply_text("No file within the upload limit was produced.")
                return
            with files[0].open("rb") as media:
                await msg.reply_document(media)


async def shorten(update, context):
    try:
        url = public_url(context.args[0])
    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /shorten <HTTP(S) URL>")
        return
    code = await asyncio.to_thread(context.bot_data["store"].shorten, url)
    await update.effective_message.reply_text(context.bot_data["short_base"].rstrip("/") + "/" + code)


async def allowlisted(update, context):
    # Configure this starter for trusted users. Public bots need product-specific quotas.
    from telegram.ext import ApplicationHandlerStop
    if update.effective_user and update.effective_user.id in context.bot_data["allowed_users"]:
        return
    if update.callback_query:
        await update.callback_query.answer("Access unavailable.")
    raise ApplicationHandlerStop


async def on_error(update, context):
    LOG.error("Recipe operation failed: %s", type(context.error).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["moderation", "reminders", "quiz", "rss", "ai", "download", "shortener"])
    args = parser.parse_args()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    allowed = {int(x.strip()) for x in os.environ["BOT_ALLOWED_USER_IDS"].split(",") if x.strip()}
    if not allowed:
        raise ValueError("BOT_ALLOWED_USER_IDS must contain at least one user ID")
    app = Application.builder().token(token).concurrent_updates(False).build()
    app.bot_data.update(store=Store(os.getenv("RECIPE_DB", "recipes.db")), allowed_users=allowed)
    if args.mode != "moderation":
        app.add_handler(MessageHandler(filters.ALL, allowlisted), group=-1)
        app.add_handler(CallbackQueryHandler(allowlisted), group=-1)
    if args.mode == "moderation":
        # Moderate all users' messages, but /warn is independently admin-authorized.
        app.add_handler(CommandHandler("warn", warn))
        app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, anti_link))
    elif args.mode == "reminders":
        app.add_handler(CommandHandler("remind", remind))
        app.job_queue.run_repeating(tick, interval=30, first=5)
    elif args.mode == "quiz":
        app.add_handler(CommandHandler("quiz", quiz))
        app.add_handler(CallbackQueryHandler(answer, pattern=r"^q:"))
    elif args.mode == "rss":
        app.bot_data.update(feeds=[public_url(x.strip()) for x in os.environ["RSS_FEEDS"].split(",") if x.strip()],
                            channel=os.environ["RSS_CHANNEL"])
        app.job_queue.run_repeating(publish, interval=600, first=5)
    elif args.mode == "ai":
        app.bot_data["model"] = os.environ["OPENAI_MODEL"]
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
    elif args.mode == "download":
        app.bot_data.update(download_hosts={x.strip().lower() for x in os.environ["DOWNLOAD_HOSTS"].split(",") if x.strip()},
                            download_limit=asyncio.Semaphore(1))
        app.add_handler(CommandHandler("dl", download))
    elif args.mode == "shortener":
        app.bot_data["short_base"] = public_url(os.environ["SHORT_BASE_URL"])
        app.add_handler(CommandHandler("shorten", shorten))
    app.add_error_handler(on_error)
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
