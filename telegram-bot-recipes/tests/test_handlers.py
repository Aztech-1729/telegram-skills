"""Authorization regressions with fake Telegram objects and no network calls."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets'))
from recipes import warn


class ModerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_admin_cannot_write_warning_or_ban(self):
        store = SimpleNamespace(warn=Mock())
        bot = SimpleNamespace(get_chat_member=AsyncMock(return_value=SimpleNamespace(status='member')),
                              ban_chat_member=AsyncMock())
        message = SimpleNamespace(chat_id=-100, reply_text=AsyncMock(),
                                  reply_to_message=SimpleNamespace(from_user=SimpleNamespace(id=8)))
        update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=7),
                                 effective_chat=SimpleNamespace(type='supergroup'))
        await warn(update, SimpleNamespace(bot=bot, bot_data={'store': store}))
        store.warn.assert_not_called()
        bot.ban_chat_member.assert_not_awaited()
        message.reply_text.assert_awaited_once()

    async def test_missing_bot_right_prevents_write(self):
        store = SimpleNamespace(warn=Mock())
        bot = SimpleNamespace(id=1, get_chat_member=AsyncMock(side_effect=[
            SimpleNamespace(status='administrator'), SimpleNamespace(status='member'),
            SimpleNamespace(status='administrator', can_restrict_members=False)]),
            ban_chat_member=AsyncMock())
        message = SimpleNamespace(chat_id=-100, reply_text=AsyncMock(),
                                  reply_to_message=SimpleNamespace(from_user=SimpleNamespace(id=8)))
        update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=7),
                                 effective_chat=SimpleNamespace(type='supergroup'))
        await warn(update, SimpleNamespace(bot=bot, bot_data={'store': store}))
        store.warn.assert_not_called()
        bot.ban_chat_member.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
