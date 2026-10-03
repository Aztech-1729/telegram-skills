"use strict";
const tg = window.Telegram?.WebApp;
const status = document.getElementById("status");
const input = document.getElementById("text");
const add = document.getElementById("add");
const logout = document.getElementById("logout");
let token = null; // Short-lived bearer stays in memory, never in a URL or localStorage.

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) throw new Error(response.status === 401 ? "Session expired. Reopen the app." : "Request failed. Please retry.");
  return response.json();
}

async function refresh() {
  const { todos } = await api("/api/todos");
  const list = document.getElementById("list");
  list.replaceChildren();
  for (const todo of todos) {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = todo.text;
    const button = document.createElement("button");
    button.textContent = "Delete";
    button.onclick = async () => {
      button.disabled = true;
      try { await api(`/api/todos/${todo.id}`, { method: "DELETE" }); await refresh(); }
      catch (error) { status.textContent = error.message; button.disabled = false; }
    };
    li.append(text, button);
    list.append(li);
  }
}

document.getElementById("form").onsubmit = async (event) => {
  event.preventDefault();
  if (!input.value.trim()) return;
  add.disabled = true;
  try {
    await api("/api/todos", { method: "POST", body: JSON.stringify({ text: input.value.trim() }) });
    input.value = "";
    await refresh();
    status.textContent = "Saved";
    if (tg?.isVersionAtLeast("6.1")) tg.HapticFeedback.notificationOccurred("success");
  } catch (error) { status.textContent = error.message; }
  finally { add.disabled = false; }
};

logout.onclick = async () => {
  try {
    await api("/api/logout", { method: "POST" });
    token = null;
    document.getElementById("list").replaceChildren();
    input.disabled = add.disabled = logout.disabled = true;
    status.textContent = "Signed out. Reopen the app to sign in.";
  } catch (error) { status.textContent = error.message; }
};

(async () => {
  tg?.ready();
  tg?.expand();
  if (!tg?.initData) { status.textContent = "Open this app from your bot's inline or menu button."; return; }
  try {
    const data = await api("/api/login", { method: "POST", body: JSON.stringify({ initData: tg.initData }) });
    token = data.token;
    document.querySelector("h1").textContent = `${data.name}'s todos`;
    await refresh();
    input.disabled = add.disabled = logout.disabled = false;
    status.textContent = "Ready";
  } catch (error) { status.textContent = error.message; }
})();
