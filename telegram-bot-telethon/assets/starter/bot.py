"""Minimal Telethon 1.x bot. Importing this module never authenticates or connects."""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Mapping

from telethon import Button, TelegramClient, errors, events
from telethon.sessions import StringSession
from telethon.tl import functions, types

LOG = logging.getLogger(__name__)
TOKEN = re.compile(r'^[0-9]+:[A-Za-z0-9_-]+$')
HASH = re.compile(r'^[A-Fa-f0-9]{32}$')
OWNER = re.compile(rb'^close:([0-9]+)$')


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    bot_token: str
    session_string: str | None = None
    session_file: str = 'mtproto-bot'

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Config:
        env = os.environ if environ is None else environ
        try:
            api_id = int(env.get('API_ID', ''))
        except ValueError as exc:
            raise ValueError('API_ID must be a positive integer') from exc
        if api_id <= 0:
            raise ValueError('API_ID must be a positive integer')
        api_hash = env.get('API_HASH', '')
        bot_token = env.get('BOT_TOKEN', '')
        if not HASH.fullmatch(api_hash):
            raise ValueError('API_HASH must be the 32-character API credential')
        if not TOKEN.fullmatch(bot_token):
            raise ValueError('BOT_TOKEN is missing or malformed')
        session_file = env.get('TG_SESSION_FILE', 'mtproto-bot')
        if not session_file:
            raise ValueError('TG_SESSION_FILE must be nonempty')
        return cls(api_id, api_hash, bot_token, env.get('TG_SESSION') or None, session_file)


def ensure_bot_identity(me: types.User | None, token: str) -> None:
    expected_id = int(token.split(':', 1)[0])
    if me is None or not me.bot or me.id != expected_id:
        raise RuntimeError('The authorized session does not match the requested bot')


def close_data(sender_id: int) -> bytes:
    if sender_id <= 0:
        raise ValueError('A callback owner must be a positive user ID')
    data = f'close:{sender_id}'.encode('ascii')
    if len(data) > 64:
        raise ValueError('Callback data exceeds 64 bytes')
    return data


def callback_owner(data: bytes | None) -> int | None:
    if not isinstance(data, bytes) or len(data) > 64:
        return None
    match = OWNER.fullmatch(data)
    if not match:
        return None
    owner = int(match.group(1))
    return owner if owner > 0 else None


def build_client(config: Config) -> TelegramClient:
    session = StringSession(config.session_string) if config.session_string else config.session_file
    return TelegramClient(
        session, config.api_id, config.api_hash,
        request_retries=3, connection_retries=3, retry_delay=1,
        flood_sleep_threshold=30, sequential_updates=False,
    )


async def menu(event: events.NewMessage.Event) -> None:
    if event.sender_id is None:
        return
    await event.respond(
        'Send private text to echo it, or close this menu.',
        parse_mode=None,
        buttons=[[Button.inline('Close', close_data(event.sender_id))]],
    )
    raise events.StopPropagation


async def echo(event: events.NewMessage.Event) -> None:
    text = event.raw_text
    if text and not text.startswith('/'):
        await event.respond(text, parse_mode=None)


async def close_menu(event: events.CallbackQuery.Event) -> None:
    owner = callback_owner(event.data)
    if owner is None or owner != event.sender_id:
        await event.answer('This menu belongs to another user.', alert=True)
        return
    await event.answer()
    try:
        await event.edit('Menu closed.', buttons=None, parse_mode=None)
    except errors.MessageNotModifiedError:
        pass


async def expired_menu(event: events.CallbackQuery.Event) -> None:
    await event.answer('This menu expired. Open /menu again.')


def register_handlers(client: TelegramClient) -> None:
    client.add_event_handler(menu, events.NewMessage(
        incoming=True, pattern=r'^/(?:start|menu)(?:@\w+)?(?:\s.*)?$',
        func=lambda e: e.is_private,
    ))
    client.add_event_handler(echo, events.NewMessage(
        incoming=True, func=lambda e: e.is_private and bool(e.raw_text) and not e.raw_text.startswith('/'),
    ))
    client.add_event_handler(close_menu, events.CallbackQuery(func=lambda e: callback_owner(e.data) is not None))
    client.add_event_handler(expired_menu, events.CallbackQuery(func=lambda e: callback_owner(e.data) is None))


async def main() -> None:
    config = Config.from_env()
    client = build_client(config)
    # Authenticate and verify identity before exposing handlers to updates.
    try:
        await client.start(bot_token=config.bot_token)
        ensure_bot_identity(await client.get_me(), config.bot_token)
        register_handlers(client)
        await client(functions.bots.SetBotCommandsRequest(
            scope=types.BotCommandScopeDefault(),
            lang_code='',
            commands=[
                types.BotCommand(command='start', description='Start'),
                types.BotCommand(command='menu', description='Show menu'),
            ],
        ))
        await client.run_until_disconnected()
    finally:
        await client.disconnect()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Telethon logs handler failures; disable detailed protocol debugging.
    logging.getLogger('telethon').setLevel(logging.WARNING)
    asyncio.run(main())
