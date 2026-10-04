# Mini App implementation guide

Checked 2026-10-04. Contents: launch contexts; bot entry points; auth/session design; native UI; persistent todo example; deployment/testing. Read [sources](sources.md) for verified documentation scope. The security/storage design below is an original example, not a claim that Telegram supplies application authorization.

## Choose launch context first

| Launch | Identity / return behavior | Design consequence |
|---|---|---|
| Reply `KeyboardButton.web_app` | Empty initData; `WebApp.sendData` returns a service message and closes | Use for constrained input; bot authenticates the incoming update sender |
| Inline `InlineKeyboardButton.web_app` | Signed context; `query_id` for `answerWebAppQuery` | Private bot chat; use backend auth for a full application |
| Menu button | Same behavior as inline button | Persistent shortcut to an authenticated application |
| Main/profile or direct link | Signed context and start parameters as documented; no chat-reading/sending permission | Treat chat-instance/start params as context; user picks inline content when sharing |
| Inline-query results button | Empty initData; return via `switchInlineQuery` and user-selected result | Do not assume signed user login is available |
| Attachment menu | Context/query flow with production eligibility restrictions | Verify account eligibility before proposing this UX |
| Join-request Mini App | Join-request query flow | Use the dedicated completion methods rather than ordinary Web App queries |

The official page's headline list of seven launch paths now also describes join-request launch. Read the relevant section rather than promising a fixed exhaustive count. [Launch documentation](https://core.telegram.org/bots/webapps#implementing-mini-apps)

## Bot entry points

PTB fragment using the configured HTTPS URL, for a private bot chat:

```python
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo

url = os.environ["MINIAPP_URL"]  # full app URL, including path if needed
await update.effective_message.reply_text(
    "Open your todos",
    reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("Open app", web_app=WebAppInfo(url)),
    ]]),
)
await context.bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(text="Todos", web_app=WebAppInfo(url)),
)
```

For aiogram 3 use `InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Open app", web_app=WebAppInfo(url=url))]])` and `bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Todos", web_app=WebAppInfo(url=url)))`. Import these types from `aiogram.types`. Configure the desired Main Mini App/menu/domain in BotFather. Domain-bound login URLs are a separate login mechanism; do not apply its registration assumptions to every Mini App launch.

## Authentication and sessions

The helper implements bot-token HMAC validation:

1. Bound the input size and field count; strictly decode the query as UTF-8. Reject malformed percent escapes and duplicate decoded keys, including duplicate hash/user fields.
2. Remove `hash`; sort the remaining decoded fields into newline-delimited key/value entries. Derive the secret with HMAC-SHA256 keyed by `WebAppData` over the bot token; compare the resulting data signature in constant time.
3. Require a fresh integer `auth_date`, allow a small explicit future clock skew, and parse a valid numeric user ID. Reject duplicate JSON keys too.
4. Issue an independent random bearer token with server-side expiry and revoke/logout support. Store a token hash, not plaintext tokens, in the database. Every todo operation obtains its owner from the stored session.

Read [official HMAC and third-party verification](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app) before adapting it. HMAC excludes `hash`; third-party Ed25519 excludes `hash` **and** `signature` and includes a bot-ID prefix. Do not mix those rules. Third-party validation can avoid sharing the bot token, but requires a verified Ed25519 implementation/public key and the same freshness/authorization policy.

The helper's five-minute freshness window, 30-second skew, one-hour bearer lifetime and input limits are example policies. HMAC proves integrity, not one-time use: a stolen recent initData blob can be replayed during its acceptance window. Use TLS, short windows, login rate limits and revocation; never log raw initData or sessions. For a truly one-use operation, atomically consume an application nonce bound to the verified user. Do not treat a user-ID keyed cache as authentication. Reusing validated sessions is appropriate; a universal ban on revalidating initData is not.

Bearer sessions stay in the frontend's memory. This example uses no ambient cookies and requires the exact same origin on mutations, so it does not need a cookie CSRF pattern. If adopting cookies, add Secure/HttpOnly/SameSite attributes and explicit CSRF protection; if adopting cross-origin hosting, design CORS/credential policy deliberately. Origin checks complement authentication; arbitrary clients can forge Origin. Enforce record ownership in SQL regardless.

## Native UI and features

Read [Mini App design](../../telegram-bot-miniapp-design/SKILL.md) for theme/color
pairs, responsive forms and native-control lifecycle. Read
[Accessibility](../../telegram-bot-accessibility/SKILL.md) for labels, focus,
contrast and actual acceptance checks. A hardcoded brand color is an optional
product choice; Telegram's theme pair is the starting point for native controls.

Load `https://telegram.org/js/telegram-web-app.js` in the head before application code. `tg.ready()` hides the loader; `expand()` expands available height rather than requesting fullscreen. Use `themeParams`/theme CSS variables, stable viewport sizing and content safe areas. Keep layout functional outside the WebView for diagnostics without granting a fake identity.

The primary action can use:

```javascript
const tg = window.Telegram.WebApp;
tg.MainButton.setParams({ text: "Save", color: "#2563eb", text_color: "#ffffff" });
tg.MainButton.onClick(async () => {
  tg.MainButton.showProgress();
  try { await saveOnAuthenticatedBackend(); }
  finally { tg.MainButton.hideProgress(); }
});
tg.MainButton.show();
```

This is an integration fragment; `saveOnAuthenticatedBackend` is your application operation. MainButton/SecondaryButton are `BottomButton` objects. Remove handlers with `offClick` during screen cleanup. BackButton follows application routing; popup destructive/cancel types are semantic styles. Do not invent `color_id`/`text_color_id` for popup/dialog keyboards.

Select conditional APIs from the official JS docs: haptics, closing confirmation, vertical-swipe controls, fullscreen, safe-area updates, sharing/prepared messages, QR scanning, contact/write-access requests, location and motion sensors. Gate by `isVersionAtLeast` and handle permission-denied/unsupported events. Avoid enabling sensors when the task does not need them; stop subscriptions on teardown.

Storage choice is functional: CloudStorage for small cross-device bot/user values, DeviceStorage for client-local state, SecureStorage for sensitive local items where supported. These do not replace backend ownership checks or billing/entitlement records. New device storage requires API 9.0; each client's availability still matters.

Open an invoice link with `tg.openInvoice(link, callback)`; show pending/cancel/error state in UI. A `paid` UI callback does not fulfill the order. The Payments skill handles server proof, duplicate deliveries, renewals and refunds.

For an authenticated checkout route, resolve the buyer with
`store.authenticated_user(bearer_token, now=int(time.time()))`. Create the order
for that verified numeric user, never an ID submitted by the browser. Query the
payment ledger's durable entitlement at each protected backend operation; a
previously issued session is authentication, not proof that paid access remains
active after a refund. Keep payment fulfillment and entitlement creation atomic.

## Persistent todo example

[assets/todo/app.py](../assets/todo/app.py) plus its HTML/JS/CSS files form a runnable backend/frontend. It imports [the helper](../scripts/miniapp_security.py) from the skill directory; copy both resources or adjust the import when extracting it.

Requirements: Python 3.10+, FastAPI with Pydantic 2, Uvicorn; HTTP tests also require HTTPX. Install these in an isolated environment and record the exact chosen versions. From `telegram-bot-miniapps/assets/todo` run:

```text
uvicorn app:app_factory --factory --host 127.0.0.1 --port 8000
```

Set `TELEGRAM_BOT_TOKEN` through your secret manager/environment, `MINIAPP_ORIGIN=https://app.example.com` to the **exact origin without trailing slash**, and optionally `MINIAPP_DB` to a private persistent SQLite path. `MINIAPP_URL` is the bot-side full app URL. Put a same-origin HTTPS proxy in front of the server. No Telegram calls occur when the backend starts.

The example implements login, list/add/delete, logout, strict request fields, expiring random sessions, hashed token storage, SQL ownership predicates, and persisted todos. It serves only three explicitly named public assets, never the source directory or database. The frontend uses `textContent`, checks HTTP status before updating, and re-fetches the saved list. Restarting the backend preserves active sessions and todos.

Deliberate bounds: a single-host SQLite example, at most 500 returned todos, no distributed rate limiter, no migrations/backup orchestration, and no automatic bot setup. Add reverse-proxy body limits (including chunked requests), request timeouts, login/action rate limits, database quotas/pagination, backups, security-header review and operational monitoring before internet deployment. Persistent database access is synchronous in FastAPI's worker thread handlers, not blocking an async event loop.

## Deployment and testing

Keep origin protection enabled; July 2026's default protection has an explicit BotFather opt-out, not an unconditional domain-registration rule. Serve production HTTPS. The documented HTTP-without-TLS exception is Telegram's separate **test environment**; ordinary localhost is not a blanket production allowance. Test/staging credentials and Telegram test-server accounts must stay separate.

Use appropriate cache policy: HTML/auth/API responses must not expose credentials through caches; version public static assets if caching them. Test iOS/Android/desktop/Web clients, theme changes, narrow viewports, keyboard/safe-area shifts, lost network, canceled native prompts and unsupported APIs.

Run offline validation from the repo root:

```text
python -m unittest discover -s telegram-bot-miniapps/scripts -p 'test_*.py' -v
```

Tests cover encoded Unicode/plus signs, tampering, duplicate keys, invalid users, stale/future dates, wrong bot token, guessed IDs as sessions, revocation, cross-user deletion, restart persistence, origin policy and public-file boundaries. These tests do not certify real client rendering or external HTTPS hosting.

Run `node --test telegram-bot-miniapps/scripts/test_frontend.mjs` for the frontend
behavior checks. The example now distinguishes primary Add from neutral Reload/
Sign out and destructive Delete, supports all four content safe insets, preserves
failed input, blocks duplicate in-flight commits and locks/clears records after
session expiry. Delete requires an explicit per-item confirmation and offers Keep
todo; successful deletion moves focus to the named list heading. Timed-out or
server-unconfirmed writes lock new commits until a successful reload; users must
check the saved list before resubmitting. Known successful writes stay reported as
saved even if the following refresh fails. Input focus returns after controls are
enabled, and whitespace-only values get an accessible error. No write is retried automatically.
These tests use a minimal fake DOM/transport and do not replace screen-reader or
actual WebView checks. Todo creation is not an idempotent business ledger; for
high-value writes, implement operation IDs and server reconciliation.
