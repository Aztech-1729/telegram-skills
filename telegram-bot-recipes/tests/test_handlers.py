"""Authorization regressions with fake Telegram objects and no network calls."""
from pathlib import Path
import asyncio
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'assets'))
from recipes import warn, answer, remind, reminder_failure, download
from telegram.error import Forbidden, RetryAfter, TimedOut, BadRequest


class ModerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_anonymous_sender_chat_cannot_be_attributed_to_a_user(self):
        store = SimpleNamespace(warn=Mock())
        bot = SimpleNamespace(get_chat_member=AsyncMock(), ban_chat_member=AsyncMock())
        message = SimpleNamespace(chat_id=-100, sender_chat=SimpleNamespace(id=-100), reply_text=AsyncMock())
        update = SimpleNamespace(effective_message=message, effective_user=SimpleNamespace(id=7),
                                 effective_chat=SimpleNamespace(type='supergroup'))
        await warn(update, SimpleNamespace(bot=bot, bot_data={'store': store}))
        store.warn.assert_not_called()
        bot.get_chat_member.assert_not_awaited()

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


class InteractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_download_does_not_upload_even_if_a_file_exists(self):
        message = SimpleNamespace(reply_text=AsyncMock(), reply_document=AsyncMock())
        context = SimpleNamespace(args=['https://example.org/video'], bot_data={
            'download_hosts': {'example.org'}, 'download_limit': asyncio.Semaphore(1)})
        created = []
        async def fake_process(*args, **kwargs):
            output = Path(args[args.index('--output') + 1].replace('%(ext)s', 'mp4'))
            output.write_bytes(b'partial data')
            created.append(output.parent)
            return SimpleNamespace(returncode=1, wait=AsyncMock(return_value=1))
        with patch('recipes.asyncio.create_subprocess_exec', side_effect=fake_process):
            await download(SimpleNamespace(effective_message=message), context)
        message.reply_document.assert_not_awaited()
        self.assertFalse(created[0].exists())

    async def test_download_cancellation_reaps_process_and_cleans_directory(self):
        message = SimpleNamespace(reply_text=AsyncMock(), reply_document=AsyncMock())
        context = SimpleNamespace(args=['https://example.org/video'], bot_data={
            'download_hosts': {'example.org'}, 'download_limit': asyncio.Semaphore(1)})
        process = SimpleNamespace(returncode=None, wait=AsyncMock(side_effect=[asyncio.CancelledError, None]), kill=Mock())
        created = []
        async def fake_process(*args, **kwargs):
            created.append(Path(args[args.index('--output') + 1]).parent)
            return process
        with patch('recipes.asyncio.create_subprocess_exec', side_effect=fake_process):
            with self.assertRaises(asyncio.CancelledError):
                await download(SimpleNamespace(effective_message=message), context)
        process.kill.assert_called_once()
        self.assertEqual(process.wait.await_count, 2)
        self.assertFalse(created[0].exists())

    async def test_stale_answer_is_a_callback_alert_without_private_send(self):
        query = SimpleNamespace(answer=AsyncMock(), data='q:unknown:0:0', from_user=SimpleNamespace(id=7),
                                message=SimpleNamespace(chat=SimpleNamespace(id=-100)))
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()),
                                  bot_data={'store': SimpleNamespace(answer=Mock(side_effect=ValueError))})
        await answer(SimpleNamespace(callback_query=query), context)
        query.answer.assert_awaited_once()
        self.assertTrue(query.answer.call_args.kwargs['show_alert'])
        context.bot.send_message.assert_not_awaited()

    async def test_reminder_rejects_oversized_astral_text_before_storage(self):
        message = SimpleNamespace(reply_text=AsyncMock(), chat_id=1)
        store = SimpleNamespace(remind=Mock())
        await remind(SimpleNamespace(effective_message=message),
                     SimpleNamespace(args=['1m', '😀' * 2000], bot_data={'store': store}))
        store.remind.assert_not_called()
        message.reply_text.assert_awaited_once()

    def test_reminder_failure_policy_separates_permanent_and_retry_delays(self):
        self.assertIsNone(reminder_failure(Forbidden('blocked'), 1))
        self.assertIsNone(reminder_failure(BadRequest('wrong chat'), 1))
        self.assertEqual(reminder_failure(TimedOut(), 2), 60)
        self.assertEqual(reminder_failure(RetryAfter(90), 1), 91)

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
