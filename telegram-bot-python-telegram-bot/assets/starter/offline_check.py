"""Offline behavior checks: no initialize(), polling, webhooks, or Telegram calls."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from telegram.ext import ConversationHandler, PicklePersistence

import bot

FAKE_TOKEN = "123456:offline-placeholder"


class StarterChecks(unittest.IsolatedAsyncioTestCase):
    async def test_minute_delay_reaches_scheduler_in_seconds(self):
        reply = AsyncMock()
        queue = SimpleNamespace(run_once=Mock())
        update = SimpleNamespace(
            effective_message=SimpleNamespace(reply_text=reply),
            effective_chat=SimpleNamespace(id=10),
        )
        context = SimpleNamespace(args=["30", "Buy", "milk"], job_queue=queue)
        await bot.remind(update, context)
        queue.run_once.assert_called_once_with(
            bot.deliver_reminder, when=1800.0, chat_id=10, data="Buy milk"
        )

    async def test_invalid_delay_never_schedules(self):
        for value in ("0", "-1", "nan", "inf", "x", "43201"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bot.parse_reminder([value])

    async def test_builder_keeps_conversations_sequential(self):
        app = bot.build_application(FAKE_TOKEN)
        self.assertEqual(app.concurrent_updates, 1)
        self.assertIsNotNone(app.job_queue)
        self.assertIsNotNone(app.updater)
        self.assertIsInstance(app.handlers[0][0], ConversationHandler)
        self.assertFalse(app.handlers[0][0].persistent)

    async def test_conversation_state_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.pkl"
            app = bot.build_application(FAKE_TOKEN, path)
            conversation = app.handlers[0][0]
            self.assertTrue(conversation.persistent)
            persistence = app.persistence
            await persistence.update_conversation(conversation.name, (10, 20), bot.ASK_AGE)
            await persistence.flush()
            restored = PicklePersistence(filepath=path)
            self.assertEqual(
                await restored.get_conversations(conversation.name), {(10, 20): bot.ASK_AGE}
            )

    async def test_foreign_callback_cannot_edit(self):
        query = SimpleNamespace(
            data="menu:close:20", from_user=SimpleNamespace(id=99),
            answer=AsyncMock(), edit_message_text=AsyncMock(),
        )
        await bot.close_menu(SimpleNamespace(callback_query=query), SimpleNamespace())
        query.answer.assert_awaited_once_with("This menu belongs to another user.", show_alert=True)
        query.edit_message_text.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
