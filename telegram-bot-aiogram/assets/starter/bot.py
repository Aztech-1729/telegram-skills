"""aiogram 3 polling starter. Importing performs no network operations."""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    BotCommand, CallbackQuery, ErrorEvent, InlineKeyboardButton,
    InlineKeyboardMarkup, Message, ReplyKeyboardRemove,
)

LOGGER = logging.getLogger(__name__)


class Form(StatesGroup):
    name = State()
    age = State()


class MenuCB(CallbackData, prefix="menu"):
    action: str
    owner: int


async def start(message: Message) -> None:
    await message.answer("Use /menu, /form or /cancel. Ordinary text is echoed.")


async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("No active form.")
        return
    await message.answer("Form cancelled.", reply_markup=ReplyKeyboardRemove())
    await state.clear()


async def begin_form(message: Message, state: FSMContext) -> None:
    await message.answer("What is your name? Use /cancel to stop.")
    await state.clear()
    await state.set_state(Form.name)


async def receive_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 100:
        await message.answer("Send a name of 1 to 100 characters.")
        return
    await message.answer("How old are you? Send an integer from 0 to 130.")
    await state.update_data(name=name)
    await state.set_state(Form.age)


async def receive_age(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isascii() or not text.isdigit() or len(text) > 3 or not 0 <= int(text) <= 130:
        await message.answer("Send an integer from 0 to 130.")
        return
    data = await state.get_data()
    await message.answer(f"Demo response: {html.quote(data['name'])}, age {int(text)}.")
    await state.clear()


async def form_input_hint(message: Message) -> None:
    await message.answer("Send text for this form, or /cancel.")


async def menu(message: Message) -> None:
    if message.from_user is None:
        return
    await message.answer(
        "Example menu",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Close", callback_data=MenuCB(action="close", owner=message.from_user.id).pack())
        ]]),
    )


async def close_menu(query: CallbackQuery, callback_data: MenuCB) -> None:
    if callback_data.owner != query.from_user.id:
        await query.answer("This menu belongs to another user.", show_alert=True)
        return
    await query.answer()
    try:
        if isinstance(query.message, Message):
            await query.message.edit_text("Menu closed.", reply_markup=None)
        elif query.inline_message_id:
            await query.bot.edit_message_text(
                text="Menu closed.", inline_message_id=query.inline_message_id, reply_markup=None
            )
    except TelegramBadRequest as exc:
        if "message is not modified" not in exc.message.casefold():
            raise


async def echo(message: Message) -> None:
    await message.answer(message.text or "", parse_mode=None)


async def expired_menu(query: CallbackQuery) -> None:
    await query.answer("This menu expired. Open /menu again.")


async def on_error(event: ErrorEvent) -> bool:
    LOGGER.error("Update handler failed (%s)", type(event.exception).__name__)
    return True


def build_dispatcher(redis_url: str | None = None) -> Dispatcher:
    if redis_url:
        storage = RedisStorage.from_url(redis_url, key_builder=DefaultKeyBuilder(with_bot_id=True))
        isolation = storage.create_isolation()
    else:
        storage = MemoryStorage()
        isolation = SimpleEventIsolation()
    dp = Dispatcher(storage=storage, events_isolation=isolation)
    router = Router(name="starter")
    router.message.register(cancel, Command("cancel"))
    router.message.register(begin_form, Command("form"), F.chat.type == "private")
    router.message.register(start, CommandStart())
    router.message.register(menu, Command("menu"))
    router.message.register(receive_name, Form.name, F.text, ~F.text.startswith("/"))
    router.message.register(receive_age, Form.age, F.text, ~F.text.startswith("/"))
    router.message.register(form_input_hint, StateFilter(Form.name, Form.age))
    router.message.register(echo, StateFilter(None), F.text, ~F.text.startswith("/"))
    router.callback_query.register(close_menu, MenuCB.filter(F.action == "close"))
    router.callback_query.register(expired_menu)
    router.errors.register(on_error)
    dp.include_router(router)
    return dp


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("Set BOT_TOKEN before running this Telegram bot.")
    dp = build_dispatcher(os.environ.get("REDIS_URL"))
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Show help"),
            BotCommand(command="menu", description="Open a menu"),
            BotCommand(command="form", description="Try a form"),
            BotCommand(command="cancel", description="Cancel the form"),
        ])
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(
            bot, allowed_updates=dp.resolve_used_update_types(), tasks_concurrency_limit=16,
            close_bot_session=False,
        )
    finally:
        await bot.session.close()
        await dp.fsm.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
