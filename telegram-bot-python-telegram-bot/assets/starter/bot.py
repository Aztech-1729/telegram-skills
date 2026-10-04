"""PTB polling starter. Importing this module performs no network operations."""

from __future__ import annotations

import html
import logging
import math
import os
import re
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    AIORateLimiter, Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, ConversationHandler, Defaults, MessageHandler,
    PicklePersistence, filters,
)

LOGGER = logging.getLogger(__name__)
ASK_NAME, ASK_AGE = range(2)
FORM_KEY = "starter_form"


def parse_reminder(args: list[str]) -> tuple[float, str]:
    if not args:
        raise ValueError("Usage: /remind <minutes> <text>")
    minutes = float(args[0])
    if not math.isfinite(minutes) or not 0 < minutes <= 43_200:
        raise ValueError("Minutes must be positive and at most 43200 in this demo.")
    text = " ".join(args[1:]).strip() or "Reminder!"
    if len(text) > 3500:
        raise ValueError("Reminder text is too long for this demo.")
    return minutes * 60, text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Use /menu, /form, /cancel, or /remind 1 Buy milk. Text is echoed."
        )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message and message.text:
        await message.reply_text(message.text, parse_mode=None)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message and update.effective_user:
        await update.effective_message.reply_text(
            "Example menu",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Close", callback_data=f"menu:close:{update.effective_user.id}")]
            ]),
        )


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    match = re.fullmatch(r"menu:close:([0-9]+)", query.data) if isinstance(query.data, str) else None
    if match is None or int(match.group(1)) != query.from_user.id:
        await query.answer("This menu belongs to another user.", show_alert=True)
        return
    await query.answer()
    if isinstance(query.message, Message) or query.inline_message_id:
        try:
            await query.edit_message_text("Menu closed.", reply_markup=None)
        except BadRequest as exc:
            if "message is not modified" not in exc.message.casefold():
                raise


async def expired_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer("This menu expired. Open /menu again.")


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    try:
        seconds, text = parse_reminder(context.args)
    except ValueError as exc:
        await update.effective_message.reply_text(str(exc), parse_mode=None)
        return
    if context.job_queue is None:
        await update.effective_message.reply_text("Scheduling is unavailable.")
        return
    context.job_queue.run_once(
        deliver_reminder, when=seconds, chat_id=update.effective_chat.id, data=text
    )
    await update.effective_message.reply_text(f"Scheduled in {seconds / 60:g} minutes.")


async def deliver_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    if job is not None and job.chat_id is not None:
        await context.bot.send_message(job.chat_id, job.data, parse_mode=None)


async def begin_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[FORM_KEY] = {}
    await update.effective_message.reply_text("What is your name? Use /cancel to stop.")
    return ASK_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.effective_message.text.strip()
    if not name or len(name) > 100:
        await update.effective_message.reply_text("Send a name of 1 to 100 characters.")
        return ASK_NAME
    context.user_data[FORM_KEY]["name"] = name
    await update.effective_message.reply_text("How old are you? Send an integer from 0 to 130.")
    return ASK_AGE


async def receive_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    if not text.isascii() or not text.isdigit() or len(text) > 3 or not 0 <= int(text) <= 130:
        await update.effective_message.reply_text("Send an integer from 0 to 130.")
        return ASK_AGE
    form = context.user_data[FORM_KEY]
    await update.effective_message.reply_text(
        f"Saved this demo response: {html.escape(form['name'])}, age {int(text)}."
    )
    # A failed reply must leave the conversation's data available for retry.
    context.user_data.pop(FORM_KEY)
    return ConversationHandler.END


async def form_input_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Send text for this form, or /cancel.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(FORM_KEY, None)
    await update.effective_message.reply_text("Form cancelled.")
    return ConversationHandler.END


async def configure_commands(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start", "Show help"), BotCommand("menu", "Open a menu"),
        BotCommand("form", "Try a form"), BotCommand("cancel", "Cancel the form"),
        BotCommand("remind", "Schedule a process-local reminder"),
    ])


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Update handler failed (%s)", type(context.error).__name__)


def build_application(token: str, state_file: str | Path | None = None) -> Application:
    builder = (
        Application.builder().token(token).concurrent_updates(False)
        .defaults(Defaults(parse_mode=ParseMode.HTML))
        .rate_limiter(AIORateLimiter(max_retries=2)).post_init(configure_commands)
    )
    if state_file:
        builder.persistence(PicklePersistence(filepath=state_file))
    app = builder.build()
    form = ConversationHandler(
        entry_points=[CommandHandler("form", begin_form, filters=filters.ChatType.PRIVATE)],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
                MessageHandler(filters.ALL & ~filters.COMMAND, form_input_hint),
            ],
            ASK_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_age),
                MessageHandler(filters.ALL & ~filters.COMMAND, form_input_hint),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="starter_form_v1", persistent=bool(state_file), allow_reentry=True,
    )
    app.add_handler(form)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(close_menu, pattern=r"^menu:close:[0-9]+$"))
    app.add_handler(CallbackQueryHandler(expired_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.add_error_handler(on_error)
    return app


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("Set BOT_TOKEN before running this Telegram bot.")
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    app = build_application(token, os.environ.get("BOT_STATE_FILE"))
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=False)


if __name__ == "__main__":
    main()
