---
name: |
  telegram-bot-miniapps
description: |
  Load this skill to build Telegram Mini Apps (Web Apps) attached to a bot: BotFather setup, web_app buttons and menu button, Telegram WebApp JS API (initData, theme, haptics, MainButton, popup, CloudStorage, openInvoice), backend validation and auth, theming, and a complete deployable Mini App example with the bot side in Python.
---

# Telegram Mini Apps (Web Apps) — Complete Guide

## 1. What a Mini App is

A Mini App is your HTTPS web app embedded in Telegram's UI (mobile and desktop), launched from a bot via a keyboard button, menu button, inline mode, direct link, or a bot chat attachment. It gets Telegram identity, theme, payments, and native dialogs through the **Telegram WebApp JS API**. Bots commonly use it for dashboards, catalogs, games, and full web UIs that chat alone can't express.

Requirements: HTTPS (or localhost for dev), served as a normal web page including the SDK early:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <script>
    const tg = window.Telegram.WebApp;
    tg.ready();                 // signal the app is loaded
    tg.expand();                // take full height
  </script>
</body>
</html>
```

## 2. Bot-side setup

```python
# PTB — attach to a message
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp

kb = InlineKeyboardMarkup([[
    InlineKeyboardButton("🚀 Open app", web_app=WebAppInfo("https://app.example.com")),
]])
await update.message.reply_text("Launch:", reply_markup=kb)

# Set the persistent menu button
await context.bot.set_chat_menu_button(
    chat_id=None,   # default for all chats
    menu_button=MenuButtonWebApp(text="Open app", web_app=WebAppInfo("https://app.example.com")),
)

# aiogram 3
from aiogram.types import WebAppInfo, MenuButtonWebApp
await message.answer("Launch:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚀 Open app", web_app=WebAppInfo(url="https://app.example.com"))],
]))
```

Configure in BotFather: `/mybots` → Bot Settings → Menu Button, and register the domain for the app. Mini App methods are origin-restricted to the app's registered domain (Telegram hardens this for all apps since July 20, 2026; configure via the BotFather Mini App settings).

## 3. WebApp JS API — the essentials

```javascript
const tg = window.Telegram.WebApp;

// Identity & context
tg.initData;                 // signed query string — send to your backend for auth
tg.initDataUnsafe;           // PARSED but UNSAFE — never trust server-side decisions
tg.initDataUnsafe.user;      // { id, first_name, last_name, username, photo_url, ... }
tg.colorScheme;              // 'light' | 'dark'
tg.themeParams;              // accent_color, bg_color, text_color, ...
tg.platform;                 // ios, android, web, macos, ...
tg.version;                  // API version
tg.isExpanded;

// Lifecycle
tg.ready(); tg.expand(); tg.close();

// UI controls
tg.MainButton.setText("Buy").show().onClick(() => tg.MainButton.sendData("buy"));
// sendData → bot receives the data string via a service message (if bot launched the app)
tg.MainButton.showProgress(false); tg.MainButton.hideProgress();

tg.BackButton.show(); tg.BackButton.onClick(() => history.back());

tg.showPopup({
  title: "Confirm",
  message: "Delete this item?",
  buttons: [{ id: "yes", type: "destructive", text: "Delete" }, { type: "cancel", text: "Cancel" }],
}, (id) => { if (id === "yes") doDelete(); });
tg.showAlert("Saved!"); tg.showConfirm("Sure?", (ok) => {});
tg.HapticFeedback.impactOccurred("medium");
tg.HapticFeedback.notificationOccurred("success");
tg.openLink("https://example.com");     // external browser
tg.openTelegramLink("https://t.me/durov");
tg.openInvoice(invoiceLink);            // Stars invoice link (create_invoice_link)

// Cloud storage (per-bot, per-user, synced across devices)
tg.CloudStorage.setItem("key", "value", (err, success) => {});
tg.CloudStorage.getItem("key", (err, value) => {});
tg.CloudStorage.getItems(["a", "b"], (err, values) => {});
tg.CloudStorage.removeItem("key", (err) => {});
tg.CloudStorage.getKeys((err, keys) => {});

// Events
tg.onEvent("themeChanged", () => applyTheme(tg.themeParams));
tg.onEvent("viewportChanged", (e) => {});
tg.enableClosingConfirmation();   // "are you sure you want to close?"
tg.disableVerticalSwipes?.();     // API 7.7+ — stop swipe-to-close during interaction
```

Version gating: wrap newer APIs — `if (tg.isVersionAtLeast("7.7")) tg.disableVerticalSwipes();`

Colors (the only place in Telegram where buttons truly support colors):

```javascript
// MainButton: full RGB
tg.MainButton.setParams({ color: "#32AEEF", text_color: "#FFFFFF", is_active: true });

// Popup buttons: style types, not RGB
tg.showPopup({ title: "Delete?", message: "This cannot be undone.",
  buttons: [
    { id: "del", type: "destructive", text: "Delete" },   // red
    { type: "cancel", text: "Cancel" },
  ]});

// Mini App keyboard buttons (dialogs): fixed palette via color_id
// 0 red, 1 orange, 2 purple, 3 green, 4 cyan, 5 blue, 6 pink (customizable by app themes)
// text_color_id uses the same palette.
```

## 4. Backend auth — validate initData (critical)

The web app authenticates by sending the raw `initData` string to your backend; validate the HMAC and then trust the parsed user:

```python
import hmac, hashlib, json
from urllib.parse import unquote, parse_qsl

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Return the parsed data dict if valid, else None."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        return None
    if abs(time.time() - int(pairs.get("auth_date", 0))) > 86400:
        return None                       # stale — reject
    if "user" in pairs:
        pairs["user"] = json.loads(pairs["user"])
    return pairs
```

Frontend:

```javascript
fetch("/api/login", { method: "POST", body: new URLSearchParams({ initData: tg.initData }) })
  .then(r => r.json())
  .then(({ token }) => { /* use your own session token for subsequent calls */ });
```

Issue your own session token after validation; never re-validate initData on every request (rate-limit it and cache by user id).

`initDataUnsafe` is for display only (e.g., greeting with the first name) — any security decision must use the HMAC-validated `initData`.

## 5. Full working example — todo Mini App

`app.py` (bot side, PTB):

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Your todos:", reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("Open Mini App", web_app=WebAppInfo("https://app.example.com")),
    ]]))

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

`server.py` (FastAPI backend serving the app + API):

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
import hmac, hashlib, json, time
from urllib.parse import parse_qsl

app = FastAPI()
TOKEN = "123:AAE..."
SESSIONS = {}   # demo only — use Redis/DB in production

def validate_init_data(init_data: str) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received = pairs.pop("hash", "")
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received):
        raise HTTPException(401)
    if abs(time.time() - int(pairs.get("auth_date", 0))) > 86400:
        raise HTTPException(401, "stale")
    return pairs

@app.post("/api/login")
async def login(request: Request):
    form = await request.form()
    data = validate_init_data(str(form["initData"]))
    user = json.loads(data["user"])
    session = user["id"]
    SESSIONS[session] = user
    return {"ok": True, "name": user.get("first_name"), "session": session}

@app.post("/api/todos")
async def add_todo(request: Request):
    body = await request.json()
    # save to DB keyed by body["session"] ...
    return {"ok": True}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

`static/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    body { background: var(--tg-theme-bg-color); color: var(--tg-theme-text-color);
           font-family: -apple-system, sans-serif; margin: 0; }
    input, button { background: var(--tg-theme-secondary-bg-color); color: var(--tg-theme-text-color);
                    border: 1px solid var(--tg-theme-hint-color); border-radius: 8px; padding: 10px; }
    .accent { color: var(--tg-theme-accent-text-color); }
  </style>
</head>
<body>
  <h3 class="accent">My todos</h3>
  <input id="t" placeholder="New todo">
  <button id="add">Add</button>
  <ul id="list"></ul>
  <script>
    const tg = window.Telegram.WebApp;
    tg.ready(); tg.expand();
    let session = null;

    fetch("/api/login", { method: "POST",
      body: new URLSearchParams({ initData: tg.initData }) })
      .then(r => r.json())
      .then(d => { session = d.session; document.querySelector("h3").textContent = `${d.name}'s todos`; });

    document.getElementById("add").onclick = () => {
      const t = document.getElementById("t").value.trim();
      if (!t) return;
      fetch("/api/todos", { method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ session, text: t }) })
        .then(() => {
          const li = document.createElement("li");
          li.textContent = t;
          document.getElementById("list").append(li);
          document.getElementById("t").value = "";
          tg.HapticFeedback.notificationOccurred("success");
        });
    };
  </script>
</body>
</html>
```

## 6. Deployment notes

- Serve HTTPS only (Caddy/nginx + ACME, or Cloudflare Pages/Vercel for static frontends + API host).
- Set proper `Cache-Control` headers; Mini Apps are cached aggressively during development — bump a query string or set no-cache on the HTML.
- The registered domain in BotFather must match the serving origin (origin restrictions are enforced).
- For local dev, use `localhost` (allowed without TLS) or a tunnel (cloudflared/ngrok) with HTTPS.
- Mobile = WebView quirks: test on both iOS and Android WebViews; avoid heavy JS bundles; Telegram throttles animations sometimes.

## 7. Checklist

- [ ] SDK loaded before `ready()`; `tg.expand()` on load
- [ ] initData validated server-side (HMAC + freshness); own session token issued
- [ ] Theme via `tg-theme-*` CSS variables; reacts to `themeChanged`
- [ ] `MainButton` used for the primary action; loading state via `showProgress`
- [ ] Haptics for success/error feedback; popups for confirmations
- [ ] API calls authorized by session, never by trusting `initDataUnsafe`
- [ ] Version-gated new APIs with `isVersionAtLeast`
- [ ] HTTPS + correct domain registered in BotFather
- [ ] Stars invoices via `create_invoice_link` + `openInvoice` when selling digital goods in-app
