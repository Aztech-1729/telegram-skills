"""Offline regression checks; no connection, login, or Telegram calls."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from telethon import Button, TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl import alltlobjects, functions, types

from bot import Config, callback_owner, close_data, close_menu, echo, ensure_bot_identity, expired_menu, menu, register_handlers


class FakeEvent:
    def __init__(self, *, sender_id: int = 42, data: bytes = b'close:42', text: str = '<plain>'):
        self.sender_id, self.data, self.raw_text = sender_id, data, text
        self.actions: list[tuple[str, object, dict]] = []

    async def respond(self, text, **kwargs):
        self.actions.append(('respond', text, kwargs))

    async def answer(self, text=None, **kwargs):
        self.actions.append(('answer', text, kwargs))

    async def edit(self, text, **kwargs):
        self.actions.append(('edit', text, kwargs))


class OfflineTests(unittest.IsolatedAsyncioTestCase):
    def test_config_rejects_missing_or_malformed_credentials(self):
        with self.assertRaises(ValueError):
            Config.from_env({})
        config = Config.from_env({'API_ID': '12345', 'API_HASH': 'a' * 32, 'BOT_TOKEN': '123456:offline'})
        self.assertEqual(config.api_id, 12345)
        with self.assertRaises(ValueError):
            Config.from_env({'API_ID': '-1', 'API_HASH': 'a' * 32, 'BOT_TOKEN': '123456:offline'})

    def test_existing_session_must_match_bot_token(self):
        ensure_bot_identity(SimpleNamespace(id=123456, bot=True), '123456:offline')
        for me in (None, SimpleNamespace(id=42, bot=True), SimpleNamespace(id=123456, bot=False)):
            with self.assertRaises(RuntimeError):
                ensure_bot_identity(me, '123456:offline')

    def test_callback_bytes_are_bounded_and_validated(self):
        self.assertEqual(callback_owner(close_data(42)), 42)
        for data in (None, 'close:42', b'close:0', b'close:-1', b'close:42:extra', b'\xff', b'x' * 65):
            self.assertIsNone(callback_owner(data))
        with self.assertRaises(ValueError):
            close_data(10 ** 70)

    async def test_foreign_callback_is_answered_without_edit(self):
        event = FakeEvent(sender_id=99)
        await close_menu(event)
        self.assertEqual([action[0] for action in event.actions], ['answer'])
        self.assertTrue(event.actions[0][2]['alert'])

    async def test_owned_callback_answer_precedes_edit(self):
        event = FakeEvent()
        await close_menu(event)
        self.assertEqual([action[0] for action in event.actions], ['answer', 'edit'])
        self.assertIsNone(event.actions[1][2]['parse_mode'])

    async def test_plain_echo_and_menu_dispatch(self):
        event = FakeEvent()
        await echo(event)
        self.assertEqual(event.actions[0][1], '<plain>')
        self.assertIsNone(event.actions[0][2]['parse_mode'])
        with self.assertRaises(events.StopPropagation):
            await menu(event)
        self.assertIn('buttons', event.actions[1][2])

    async def test_stale_callbacks_use_disjoint_recovery_route(self):
        client = TelegramClient(StringSession(), 12345, 'a' * 32)
        register_handlers(client)
        routes = [(handler, builder) for handler, builder in client.list_event_handlers() if isinstance(builder, events.CallbackQuery)]
        for _, builder in routes:
            await builder.resolve(client)
        for data, expected in ((b'close:42', close_menu), (b'close:0', expired_menu), (b'old:unknown', expired_menu), (b'x' * 65, expired_menu)):
            event = FakeEvent(data=data)
            selected = [handler for handler, builder in routes if builder.filter(event)]
            self.assertEqual(selected, [expected])
        event = FakeEvent(data=b'old:unknown')
        await expired_menu(event)
        self.assertEqual(event.actions, [('answer', 'This menu expired. Open /menu again.', {})])
        game_update = types.UpdateBotCallbackQuery(query_id=1, user_id=42,
            peer=types.PeerUser(42), msg_id=2, chat_instance=3, game_short_name='offline')
        game_event = events.CallbackQuery.build(game_update)
        self.assertIsNone(game_event.data)
        self.assertEqual([handler for handler, builder in routes if builder.filter(game_event)], [expired_menu])
        game_event.answer = AsyncMock()
        await expired_menu(game_event)
        game_event.answer.assert_awaited_once_with('This menu expired. Open /menu again.')

    def test_real_v1_builders_raw_requests_and_button_families(self):
        client = TelegramClient(StringSession(), 12345, 'a' * 32)
        register_handlers(client)
        handlers = client.list_event_handlers()
        self.assertEqual(len(handlers), 4)
        self.assertIsInstance(handlers[0][1], events.NewMessage)
        self.assertIsInstance(handlers[-1][1], events.CallbackQuery)
        self.assertTrue(handlers[0][1].pattern('/menu'))
        self.assertIsNotNone(client.build_reply_markup([[Button.request_phone('Phone')]]))
        with self.assertRaises(ValueError):
            client.build_reply_markup([[Button.inline('Inline', b'a'), Button.text('Reply')]])
        request = functions.messages.GetHistoryRequest(
            peer=types.InputPeerEmpty(), offset_id=0, offset_date=None,
            add_offset=0, limit=100, max_id=0, min_id=0, hash=0,
        )
        self.assertIsInstance(bytes(request), bytes)
        for request in (
            functions.channels.JoinChannelRequest(types.InputChannelEmpty()),
            functions.messages.ImportChatInviteRequest(hash='offline-placeholder'),
            functions.account.UpdateProfileRequest(first_name='Example', about='Example'),
            functions.bots.SetBotCommandsRequest(
                scope=types.BotCommandScopeDefault(), lang_code='',
                commands=[types.BotCommand(command='start', description='Start')],
            ),
        ):
            self.assertIsInstance(bytes(request), bytes)
        self.assertEqual(alltlobjects.LAYER, 229)


if __name__ == '__main__':
    unittest.main(verbosity=2)
