"""Offline state/filter checks. Does not start polling or connect to Redis."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.filters import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import bot


class StarterChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=10, user_id=20))

    async def asyncTearDown(self):
        await self.storage.close()

    async def test_form_rejects_age_without_ending(self):
        await self.state.set_state(bot.Form.age)
        await self.state.set_data({"name": "A&B"})
        for invalid in ("yes", "131", "-1", "9" * 100):
            message = SimpleNamespace(text=invalid, answer=AsyncMock())
            await bot.receive_age(message, self.state)
            self.assertEqual(await self.state.get_state(), bot.Form.age.state)

    async def test_success_escapes_name_and_clears_state(self):
        await self.state.set_state(bot.Form.age)
        await self.state.set_data({"name": "<Ada>"})
        message = SimpleNamespace(text="30", answer=AsyncMock())
        await bot.receive_age(message, self.state)
        message.answer.assert_awaited_once_with("Demo response: &lt;Ada&gt;, age 30.")
        self.assertIsNone(await self.state.get_state())
        self.assertEqual(await self.state.get_data(), {})

    async def test_cancellation_clears_partial_data(self):
        await self.state.set_state(bot.Form.name)
        await self.state.set_data({"partial": True})
        await bot.cancel(SimpleNamespace(answer=AsyncMock()), self.state)
        self.assertIsNone(await self.state.get_state())
        self.assertEqual(await self.state.get_data(), {})

    async def test_callback_bound_and_router_subscription(self):
        packed = bot.MenuCB(action="close", owner=20).pack()
        self.assertEqual(bot.MenuCB.unpack(packed).action, "close")
        with self.assertRaises(ValueError):
            bot.MenuCB(action="x" * 65, owner=20).pack()
        dp = bot.build_dispatcher()
        self.assertEqual(set(dp.resolve_used_update_types()), {"message", "callback_query"})
        await dp.fsm.close()
        self.assertEqual(CommandObject(command="remind", args="30 Buy milk").args, "30 Buy milk")

    async def test_foreign_callback_cannot_edit(self):
        message = SimpleNamespace(edit_text=AsyncMock())
        query = SimpleNamespace(from_user=SimpleNamespace(id=99), message=message, answer=AsyncMock())
        await bot.close_menu(query, bot.MenuCB(action="close", owner=20))
        query.answer.assert_awaited_once_with("This menu belongs to another user.", show_alert=True)
        message.edit_text.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
