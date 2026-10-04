import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { makeGrammy, makeTelegraf } from './bots.mjs';

const me = { id: 123456, is_bot: true, first_name: 'Fixture', username: 'FixtureBot',
  can_join_groups: true, can_read_all_group_messages: false, supports_inline_queries: false };
const user = { id: 99, is_bot: false, first_name: 'Test' };
const msg = text => ({ message_id: 3, date: 1, chat: { id: 99, type: 'private' }, from: user,
  text, entities: text.startsWith('/') ? [{ offset: 0, length: text.length, type: 'bot_command' }] : [] });

for (const [name, factory] of [['grammY', makeGrammy], ['Telegraf', makeTelegraf]]) {
  test(`${name}: command and callback produce correct requests through a local fake API`, async () => {
    const calls = [];
    const server = createServer(async (req, res) => {
      let body = '';
      for await (const chunk of req) body += chunk;
      const method = req.url.split('/').at(-1);
      const payload = JSON.parse(body || '{}');
      calls.push({ method, payload });
      const result = method === 'getMe' ? me : method === 'answerCallbackQuery' ? true :
        { message_id: 10, date: 1, chat: { id: 99, type: 'private' }, text: payload.text ?? '' };
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify({ ok: true, result }));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const apiRoot = `http://127.0.0.1:${server.address().port}`;
    try {
      const options = name === 'grammY' ? { botInfo: me, client: { apiRoot } } : { telegram: { apiRoot } };
      const bot = factory('123456:synthetic-offline-token', options);
      bot.botInfo = me;
      await bot.handleUpdate({ update_id: 1, message: msg('/start') });
      await bot.handleUpdate({ update_id: 2, callback_query: { id: 'fixture-query', from: user,
        chat_instance: 'fixture-chat', data: 'help', message: msg('menu') } });
      assert.equal(calls.filter(x => x.method === 'sendMessage').length, 2);
      const answer = calls.find(x => x.method === 'answerCallbackQuery');
      assert.equal(answer.payload.callback_query_id, 'fixture-query');
      const first = calls.find(x => x.method === 'sendMessage');
      assert.equal(first.payload.reply_markup.inline_keyboard[0][0].callback_data, 'help');
      assert.ok(calls.indexOf(answer) < calls.findIndex((x, i) => i > 0 && x.method === 'sendMessage'));
      await bot.handleUpdate({ update_id: 3, message: { ...msg('<plain & text>'),
        chat: { id: -1001234567890, type: 'supergroup', title: 'Fixture' },
        is_topic_message: true, message_thread_id: 42 } });
      const topic = calls.at(-1).payload;
      assert.equal(topic.chat_id, -1001234567890);
      assert.equal(topic.message_thread_id, 42);
      assert.equal(topic.text, '<plain & text>');
      assert.equal(topic.parse_mode, undefined);
      await bot.handleUpdate({ update_id: 4, callback_query: { id: 'inline-query', from: user,
        chat_instance: 'fixture-inline', inline_message_id: 'fixture-message', data: 'help' } });
      assert.equal(calls.at(-1).method, 'answerCallbackQuery');
      assert.equal(calls.at(-1).payload.callback_query_id, 'inline-query');
      assert.equal(calls.at(-1).payload.text, 'Use /help or send text.');
      await bot.handleUpdate({ update_id: 5, callback_query: { id: 'stale-query', from: user,
        chat_instance: 'fixture-chat', data: 'deleted-action', message: msg('menu') } });
      assert.equal(calls.at(-1).payload.callback_query_id, 'stale-query');
      assert.equal(calls.at(-1).payload.text, 'This button is no longer available.');
      const count = calls.length;
      await bot.handleUpdate({ update_id: 6, edited_message: msg('Edited') });
      const { text: unusedText, ...nonText } = msg('');
      await bot.handleUpdate({ update_id: 7, message: { ...nonText,
        photo: [{ file_id: 'fixture', file_unique_id: 'fixture', width: 1, height: 1 }] } });
      assert.equal(calls.length, count);
      assert.ok(calls.every(x => ['sendMessage', 'answerCallbackQuery'].includes(x.method)));
    } finally {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
  });
}
