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
      assert.ok(calls.every(x => ['sendMessage', 'answerCallbackQuery'].includes(x.method)));
    } finally {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
  });
}
