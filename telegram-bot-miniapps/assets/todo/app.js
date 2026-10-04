"use strict";
const tg = window.Telegram?.WebApp;
const status = document.getElementById("status");
const input = document.getElementById("text");
const add = document.getElementById("add");
const logout = document.getElementById("logout");
const reload = document.getElementById("reload");
const list = document.getElementById("list");
let token = null; // Short-lived bearer stays in memory, never in a URL/storage.
let busy = false;
let uncertainWrite = false; // Require a successful read before another commit.

function controls() {
  input.disabled = add.disabled = !token || busy || uncertainWrite;
  logout.disabled = reload.disabled = !token || busy;
  for (const button of list.querySelectorAll("button")) button.disabled = !token || busy || uncertainWrite;
  document.getElementById("form").setAttribute("aria-busy", String(busy));
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {
      ...options, signal: controller.signal, cache: "no-store",
      headers: { "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
    });
    if (response.status === 401) {
      token = null;
      list.replaceChildren();
      document.getElementById("empty").hidden = true;
      controls();
      throw new Error("Session expired. Reopen the app to sign in.");
    }
    if (!response.ok) {
      if (response.status >= 500 && options.method && options.method !== "GET") {
        uncertainWrite = true;
        throw new Error("Server could not confirm the change. It may be saved; reload before trying again.");
      }
      throw new Error(path === "/api/todos" && options.method === "POST"
        ? "Request rejected. Your input is kept; check it before trying again."
        : "Could not complete the request. Reload to check saved todos.");
    }
    return await response.json();
  } catch (error) {
    if (["AbortError", "TypeError", "SyntaxError"].includes(error.name)) {
      if (options.method && options.method !== "GET" && token) uncertainWrite = true;
      throw new Error(options.method && options.method !== "GET"
        ? "Connection lost. The change may be saved; reload to check before trying again."
        : "Connection lost. Reload when you are online.");
    }
    throw error;
  } finally { clearTimeout(timeout); }
}

async function refresh() {
  const { todos } = await api("/api/todos");
  list.replaceChildren();
  document.getElementById("empty").hidden = todos.length !== 0;
  for (const todo of todos) {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = todo.text;
    const button = document.createElement("button");
    button.textContent = "Delete";
    button.className = "danger";
    button.setAttribute("aria-label", `Delete todo: ${todo.text}`);
    const confirmation = document.createElement("span");
    confirmation.textContent = "Delete this todo? This cannot be undone.";
    confirmation.hidden = true;
    const cancel = document.createElement("button");
    cancel.textContent = "Keep todo";
    cancel.hidden = true;
    cancel.onclick = () => {
      confirmation.hidden = cancel.hidden = true;
      button.textContent = "Delete";
      button.setAttribute("aria-label", `Delete todo: ${todo.text}`);
      button.focus();
      status.textContent = "Todo kept.";
    };
    button.onclick = () => {
      if (busy || !token || uncertainWrite) return;
      if (confirmation.hidden) {
        confirmation.hidden = cancel.hidden = false;
        button.textContent = "Confirm delete";
        button.setAttribute("aria-label", `Confirm permanent deletion of todo: ${todo.text}`);
        status.textContent = `Delete todo “${todo.text}”? This cannot be undone.`;
        button.focus();
        return;
      }
      return action(async () => {
        await api(`/api/todos/${todo.id}`, { method: "DELETE" });
        list.replaceChildren(...[...list.children].filter(item => item !== li));
        document.getElementById("list-title").focus();
        try { await refresh(); }
        catch (error) { status.textContent = `Todo deleted. ${error.message}`; return; }
        status.textContent = "Todo deleted.";
      });
    };
    li.append(text, button, confirmation, cancel);
    list.append(li);
  }
  controls();
}

async function action(operation) {
  if (busy || !token) return;
  busy = true;
  controls();
  status.textContent = "Working…";
  let focusAfter;
  try { focusAfter = await operation(); }
  catch (error) { status.textContent = error.message; }
  finally { busy = false; controls(); }
  if (focusAfter && !focusAfter.disabled) focusAfter.focus();
}

document.getElementById("form").onsubmit = (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (busy || !token || uncertainWrite) return;
  if (!text) {
    input.setAttribute("aria-invalid", "true");
    status.textContent = "Enter a todo using at least one non-space character.";
    document.getElementById("text-error").textContent = status.textContent;
    document.getElementById("text-error").hidden = false;
    input.focus(); return;
  }
  input.setAttribute("aria-invalid", "false");
  document.getElementById("text-error").textContent = "";
  document.getElementById("text-error").hidden = true;
  return action(async () => {
    await api("/api/todos", { method: "POST", body: JSON.stringify({ text }) });
    input.value = "";
    try { await refresh(); }
    catch (error) { status.textContent = `Todo saved. ${error.message}`; return input; }
    status.textContent = "Todo saved.";
    if (tg?.isVersionAtLeast("6.1")) tg.HapticFeedback.notificationOccurred("success");
    return input;
  });
};

reload.onclick = () => action(async () => {
  await refresh();
  const wasUncertain = uncertainWrite;
  uncertainWrite = false;
  status.textContent = wasUncertain
    ? "Todos reloaded. Check whether your change is present before submitting again."
    : "Todos reloaded.";
});
logout.onclick = () => action(async () => {
  await api("/api/logout", { method: "POST" });
  token = null;
  list.replaceChildren();
  document.getElementById("empty").hidden = true;
  status.textContent = "Signed out. Reopen the app to sign in.";
});

(async () => {
  tg?.ready();
  tg?.expand();
  if (!tg?.initData) { status.textContent = "Open this app from your bot's inline or menu button."; return; }
  try {
    const data = await api("/api/login", { method: "POST", body: JSON.stringify({ initData: tg.initData }) });
    token = data.token;
    document.querySelector("h1").textContent = `${data.name}'s todos`;
    await refresh();
    status.textContent = "Ready. Add a todo or manage your saved list.";
  } catch (error) { status.textContent = error.message; }
  finally { controls(); }
})();
