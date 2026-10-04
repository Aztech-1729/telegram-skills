"""Offline behavior checks: no initialize(), polling, webhooks, or Telegram calls."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from telegram import CallbackQuery, Update, User
from telegram.error import NetworkError
from telegram.ext import CallbackQueryHandler, ConversationHandler, PicklePersistence

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

    async def test_failed_completion_preserves_form_for_retry(self):
        reply = AsyncMock(side_effect=NetworkError("offline failure"))
        update = SimpleNamespace(effective_message=SimpleNamespace(text="30", reply_text=reply))
        context = SimpleNamespace(user_data={bot.FORM_KEY: {"name": "<Ada>"}, "other": True})
        with self.assertRaises(NetworkError):
            await bot.receive_age(update, context)
        self.assertEqual(context.user_data[bot.FORM_KEY], {"name": "<Ada>"})
        reply.side_effect = None
        self.assertEqual(await bot.receive_age(update, context), ConversationHandler.END)
        reply.assert_awaited_with("Saved this demo response: &lt;Ada&gt;, age 30.")
        self.assertEqual(context.user_data, {"other": True})

    async def test_failed_reentry_preserves_old_form_until_prompt_succeeds(self):
        reply = AsyncMock(side_effect=NetworkError("offline failure"))
        update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=reply))
        context = SimpleNamespace(user_data={bot.FORM_KEY: {"name": "Ada"}, "other": True})
        with self.assertRaises(NetworkError):
            await bot.begin_form(update, context)
        self.assertEqual(context.user_data[bot.FORM_KEY], {"name": "Ada"})
        reply.side_effect = None
        self.assertEqual(await bot.begin_form(update, context), bot.ASK_NAME)
        self.assertEqual(context.user_data, {bot.FORM_KEY: {}, "other": True})

    async def test_failed_cancellation_preserves_form_until_confirmation_succeeds(self):
        reply = AsyncMock(side_effect=NetworkError("offline failure"))
        update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=reply))
        context = SimpleNamespace(user_data={bot.FORM_KEY: {"name": "Ada"}, "other": True})
        with self.assertRaises(NetworkError):
            await bot.cancel(update, context)
        self.assertEqual(context.user_data[bot.FORM_KEY], {"name": "Ada"})
        reply.side_effect = None
        self.assertEqual(await bot.cancel(update, context), ConversationHandler.END)
        self.assertEqual(context.user_data, {"other": True})

    async def test_stale_callback_selects_recovery_after_specific_route(self):
        app = bot.build_application(FAKE_TOKEN)
        callbacks = [handler for handler in app.handlers[0] if isinstance(handler, CallbackQueryHandler)]
        for payload, expected in (("menu:close:20", bot.close_menu), ("old:unknown", bot.expired_menu)):
            update = Update(1, callback_query=CallbackQuery("offline", User(20, "Ada", False), "chat", data=payload))
            selected = next(handler for handler in callbacks if handler.check_update(update))
            self.assertIs(selected.callback, expected)
        query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
        await bot.expired_menu(SimpleNamespace(callback_query=query), SimpleNamespace())
        query.answer.assert_awaited_once_with("This menu expired. Open /menu again.")
        query.edit_message_text.assert_not_awaited()

    async def test_nontext_form_input_selects_hint_and_keeps_state(self):
        app = bot.build_application(FAKE_TOKEN)
        conversation = app.handlers[0][0]
        update = Update.de_json({"update_id": 2, "message": {
            "message_id": 1, "date": 1, "chat": {"id": 10, "type": "private"},
            "photo": [{"file_id": "offline", "file_unique_id": "offline", "width": 1, "height": 1}],
        }}, app.bot)
        for state in (bot.ASK_NAME, bot.ASK_AGE):
            selected = next(handler for handler in conversation.states[state] if handler.check_update(update))
            self.assertIs(selected.callback, bot.form_input_hint)
        message = SimpleNamespace(reply_text=AsyncMock())
        context = SimpleNamespace(user_data={bot.FORM_KEY: {"name": "Ada"}})
        result = await bot.form_input_hint(SimpleNamespace(effective_message=message), context)
        self.assertIsNone(result)  # ConversationHandler retains the current state.
        self.assertEqual(context.user_data[bot.FORM_KEY], {"name": "Ada"})


if __name__ == "__main__":
    unittest.main()
