import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { makeFeedbackBot } from './feedback_bot.mjs';

const me = { id: 123456, is_bot: true, first_name: 'Fixture', username: 'FixtureBot' };

async function fixture(body, { enabled = true, saveError = false } = {}) {
  const calls = [], saved = [];
  let checks = 0, update = 0;
  const server = createServer(async (request, response) => {
    let data = '';
    for await (const chunk of request) data += chunk;
    const method = request.url.split('/').at(-1);
    const payload = JSON.parse(data || '{}');
    calls.push({ method, payload });
    response.setHeader('Content-Type', 'application/json');
    response.end(JSON.stringify({ ok: true, result: {
      message_id: calls.length, date: 1, chat: { id: payload.chat_id, type: 'private' }, text: payload.text,
    } }));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const bot = makeFeedbackBot('123456:synthetic-offline-token', {
    options: { botInfo: me, client: { apiRoot: `http://127.0.0.1:${server.address().port}` } },
    canSubmit: async () => { checks++; return enabled; },
    saveFeedback: async value => {
      if (saveError) throw new Error('Private backend error must not be shown');
      saved.push(value);
      return { saved: true };
    },
  });
  async function send(text, user = 99, chatType = 'private') {
    await bot.handleUpdate({ update_id: ++update, message: {
      message_id: update, date: 1, from: { id: user, is_bot: false, first_name: 'Test' },
      chat: { id: user, type: chatType, ...(chatType === 'supergroup' ? { title: 'Fixture' } : {}) }, text,
      ...(text.startsWith('/') ? { entities: [{ type: 'bot_command', offset: 0, length: text.split(' ')[0].length }] } : {}),
    } });
  }
  try {
    await body({ send, calls, saved, checks: () => checks });
    assert.ok(calls.every(call => call.method === 'sendMessage'));
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
}

test('conversation replay checks the account once and saves only after confirmation', async () => {
  await fixture(async ({ send, calls, saved, checks }) => {
    await send('/feedback');
    await send('  ');
    await send('Useful feedback');
    await send('not a confirmation');
    assert.equal(saved.length, 0);
    await send('/confirm');
    assert.equal(checks(), 1);
    assert.deepEqual(saved, [{ key: 'feedback:123456:99:1', owner: 99, text: 'Useful feedback' }]);
    assert.equal(calls.at(-1).payload.text, 'Feedback saved. Thank you.');
    assert.equal(calls.length, 5); // Replayed prompts are not sent again.
  });
});

test('cancellation and validation bounds leave no persisted feedback', async () => {
  await fixture(async ({ send, saved, calls }) => {
    await send('/feedback');
    await send('/cancel');
    assert.match(calls.at(-1).payload.text, /Nothing was saved/);
    await send('/feedback');
    for (let i = 0; i < 3; i++) await send('😀'.repeat(501));
    assert.match(calls.at(-1).payload.text, /No feedback saved/);
    assert.deepEqual(saved, []);
  });
});

test('independent private chats cannot consume one another’s dialog', async () => {
  await fixture(async ({ send, saved }) => {
    await send('/feedback', 99);
    await send('Other user input', 100);
    await send('/confirm', 100);
    assert.deepEqual(saved, []);
    await send('Owner input', 99);
    await send('/confirm', 99);
    assert.equal(saved[0].owner, 99);
    assert.equal(saved[0].text, 'Owner input');
  });
});

test('unavailable account and group entry do not start a writable flow', async () => {
  await fixture(async ({ send, saved, checks }) => {
    await send('/feedback', 99, 'supergroup');
    assert.equal(checks(), 0);
    await send('/feedback');
    await send('Draft');
    await send('/confirm');
    assert.equal(checks(), 1);
    assert.deepEqual(saved, []);
  }, { enabled: false });
});

test('uncertain backend failure reports recovery and does not claim successful save', async () => {
  await fixture(async ({ send, calls, saved }) => {
    await send('/feedback');
    await send('Draft');
    await send('/confirm');
    assert.equal(saved.length, 0);
    assert.match(calls.at(-1).payload.text, /Saving was not confirmed/);
    assert.ok(calls.every(call => !call.payload.text.includes('Private backend error')));
  }, { saveError: true });
});
