import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFile } from 'node:fs/promises';

const script = await readFile(new URL('../assets/todo/app.js', import.meta.url), 'utf8');
class Element {
  constructor() { this.children = []; this.attributes = {}; this.value = ''; this.disabled = false; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  setAttribute(key, value) { this.attributes[key] = value; }
  focus() { if (!this.disabled) this.focused = true; }
  querySelectorAll() { return this.children.flatMap(item => item.children.filter(child => child.onclick)); }
}
const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
async function setup(handler) {
  const elements = Object.fromEntries(['status', 'text', 'text-error', 'add', 'logout', 'reload', 'list', 'empty', 'form', 'list-title', 'h1'].map(id => [id, new Element()]));
  const calls = [];
  const sandbox = {
    window: { Telegram: { WebApp: { initData: 'synthetic-fixture', ready() {}, expand() {}, isVersionAtLeast() { return false; } } } },
    document: { getElementById: id => elements[id], querySelector: () => elements.h1, createElement: () => new Element() },
    AbortController, setTimeout, clearTimeout,
    fetch: async (path, options) => {
      calls.push([path, options]);
      if (path === '/api/login') return response({ token: 'synthetic-session', name: 'Test' });
      return handler(path, options, calls);
    },
  };
  await vm.runInNewContext(script, sandbox);
  return { elements, calls };
}

test('duplicate submits produce one pending write and restore usable controls', async () => {
  let finish;
  const app = await setup((path, options) => options.method === 'POST'
    ? new Promise(resolve => { finish = resolve; }) : response({ todos: [] }));
  app.elements.text.value = 'Keep this task';
  const first = app.elements.form.onsubmit({ preventDefault() {} });
  const second = app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.calls.filter(([path, options]) => path === '/api/todos' && options.method === 'POST').length, 1);
  assert.equal(app.elements.logout.disabled, true);
  assert.equal(app.elements.form.attributes['aria-busy'], 'true');
  finish(response({ id: 1 }, 201));
  await Promise.all([first, second]);
  assert.equal(app.elements.add.disabled, false);
  assert.equal(app.elements.text.value, '');
  assert.equal(app.elements.status.textContent, 'Todo saved.');
  assert.equal(app.elements.text.focused, true);
});

test('failed write keeps user input and explains recovery', async () => {
  const app = await setup((path, options) => options.method === 'POST'
    ? response({}, 422) : response({ todos: [] }));
  app.elements.text.value = 'Still here';
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.elements.text.value, 'Still here');
  assert.match(app.elements.status.textContent, /input is kept/);
  assert.equal(app.elements.add.disabled, false);
});

test('lost connection after a write does not claim failure or retry it automatically', async () => {
  const app = await setup((path, options) => {
    if (options.method === 'POST') throw new TypeError('network unavailable');
    return response({ todos: [] });
  });
  app.elements.text.value = 'Possibly saved';
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.elements.text.value, 'Possibly saved');
  assert.match(app.elements.status.textContent, /may be saved/);
  assert.equal(app.calls.filter(([path, options]) => options.method === 'POST' && path === '/api/todos').length, 1);
  assert.equal(app.elements.add.disabled, true);
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.calls.filter(([path, options]) => options.method === 'POST' && path === '/api/todos').length, 1);
  assert.equal(app.elements.reload.disabled, false);
  await app.elements.reload.onclick();
  assert.equal(app.elements.add.disabled, false);
  assert.match(app.elements.status.textContent, /Check whether your change/);
});

test('expired session locks controls and removes stale private records', async () => {
  let expired = false;
  const app = await setup(() => expired ? response({}, 401) : response({ todos: [{ id: 1, text: '<b>Task</b>' }] }));
  const item = app.elements.list.children[0];
  assert.equal(item.children[0].textContent, '<b>Task</b>');
  assert.equal(item.children[1].attributes['aria-label'], 'Delete todo: <b>Task</b>');
  expired = true;
  await app.elements.reload.onclick();
  assert.equal(app.elements.list.children.length, 0);
  assert.equal(app.elements.add.disabled, true);
  assert.equal(app.elements.logout.disabled, true);
  assert.match(app.elements.status.textContent, /Session expired/);
});

test('successful deletion restores focus to a surviving named element', async () => {
  const app = await setup((path, options) => options.method === 'DELETE' ? response({ ok: true }) : response({ todos: [{ id: 1, text: 'Task' }] }));
  await app.elements.list.children[0].children[1].onclick();
  assert.equal(app.calls.filter(([, options]) => options.method === 'DELETE').length, 0);
  await app.elements.list.children[0].children[1].onclick();
  assert.equal(app.elements['list-title'].focused, true);
  assert.equal(app.elements.status.textContent, 'Todo deleted.');
});

test('delete confirmation can be cancelled without a write', async () => {
  const app = await setup(() => response({ todos: [{ id: 1, text: 'Keep me' }] }));
  const row = app.elements.list.children[0];
  await row.children[1].onclick();
  assert.match(row.children[1].attributes['aria-label'], /Confirm permanent/);
  row.children[3].onclick();
  assert.equal(row.children[3].hidden, true);
  assert.equal(row.children[1].textContent, 'Delete');
  assert.equal(row.children[1].focused, true);
  assert.equal(app.calls.filter(([, options]) => options.method === 'DELETE').length, 0);
});

test('confirmed write remains a success when the following read fails', async () => {
  let reads = 0;
  const app = await setup((path, options) => options.method === 'POST'
    ? response({ id: 1 }, 201) : response({ todos: [] }, ++reads === 1 ? 200 : 503));
  app.elements.text.value = 'Known saved';
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.elements.text.value, '');
  assert.match(app.elements.status.textContent, /^Todo saved\./);
  assert.equal(app.elements.add.disabled, false);
  assert.equal(app.elements.text.focused, true);
});

test('server cannot confirm a write: disable commits until a successful refresh', async () => {
  const app = await setup((path, options) => options.method === 'POST'
    ? response({}, 503) : response({ todos: [] }));
  app.elements.text.value = 'Unconfirmed';
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.elements.add.disabled, true);
  assert.match(app.elements.status.textContent, /may be saved/);
  await app.elements.reload.onclick();
  assert.equal(app.elements.add.disabled, false);
});

test('space-only input gives an accessible error without sending a write', async () => {
  const app = await setup(() => response({ todos: [] }));
  app.elements.text.value = '   ';
  await app.elements.form.onsubmit({ preventDefault() {} });
  assert.equal(app.elements.text.attributes['aria-invalid'], 'true');
  assert.equal(app.elements['text-error'].hidden, false);
  assert.match(app.elements['text-error'].textContent, /non-space character/);
  assert.match(app.elements.status.textContent, /non-space character/);
  assert.equal(app.elements.text.focused, true);
  assert.equal(app.calls.filter(([, options]) => options.method === 'POST' && options.body !== undefined).length, 1); // login only
});
