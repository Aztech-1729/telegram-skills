# Sources and researched cutoff

Checked **2026-10-03**. The baseline is **Telethon 1.45.0**, published on PyPI **2026-09-10**; the official stable documentation identified itself as 1.45.0 during research. The changelog and installed `telethon.tl.alltlobjects.LAYER` report **MTProto layer 229**. Examples deliberately use the v1 client; they are not v2 migration examples.

Package metadata advertises `Requires-Python: >=3.5`. The included starter uses modern Python syntax and therefore targets **Python 3.10+**, with offline validation on **3.12.14**. Metadata is not an interpreter compatibility test. Pin and validate upgrades; stable URLs can later move.

| Canonical primary source | Verified scope |
| --- | --- |
| [Official PyPI release metadata](https://pypi.org/pypi/Telethon/1.45.0/json) | Version, release upload date, Python metadata; no later package release used. |
| [Telethon changelog](https://docs.telethon.dev/en/stable/misc/changelog.html#new-layer-v1-45) | v1.45 layer update and release changes; no unsupported 'maintenance mode' claim inferred. |
| [Signing in](https://docs.telethon.dev/en/stable/basic/signing-in.html) | API ID/hash, interactive user login, bot-token login and saved-session reuse. |
| [Sessions](https://docs.telethon.dev/en/stable/concepts/sessions.html) | SQLite and string authorization sessions, credential sensitivity, entity storage. |
| [Asyncio](https://docs.telethon.dev/en/stable/concepts/asyncio.html) | One-loop lifecycle, sync helpers, awaiting methods and task supervision. |
| [Update concepts](https://docs.telethon.dev/en/stable/concepts/updates.html) | Event registration, dispatch, update reception and exception visibility. |
| [Events reference](https://docs.telethon.dev/en/stable/modules/events.html) | Supported builders, `NewMessage` filters, callback and inline events, propagation. |
| [Custom objects](https://docs.telethon.dev/en/stable/modules/custom.html) | Button families, request_phone, callback bytes, message and inline-result helpers. |
| [Entities](https://docs.telethon.dev/en/stable/concepts/entities.html) | Input entities, account-specific hashes, resolution and cache limitations. |
| [Client API](https://docs.telethon.dev/en/stable/modules/client.html) | Friendly methods, conversations, file inputs, default retries and sequential updates; signatures also checked against installed 1.45.0. |
| [RPC errors](https://docs.telethon.dev/en/stable/concepts/errors.html) | FloodWaitError seconds, known error classes and incomplete server error knowledge. |
| [Telegram file protocol](https://core.telegram.org/api/files) | File parts/size determined by account/server configuration; no blanket upload-size guarantee. |
| [messages.getHistory](https://core.telegram.org/method/messages.getHistory) | Required protocol fields, user-only eligibility. |
| [channels.joinChannel](https://core.telegram.org/method/channels.joinChannel) | User-only public channel joining and server errors. |
| [messages.importChatInvite](https://core.telegram.org/method/messages.importChatInvite) | Invite hash, user-only eligibility, invite/request restrictions. |
| [account.updateProfile](https://core.telegram.org/method/account.updateProfile) | Optional first/last name and about fields; user-only method scope. |

## Additional direct API verification

Installed the official `Telethon==1.45.0` distribution into an isolated temporary validation directory. Offline inspection confirmed the exact constructors for `GetHistoryRequest`, `JoinChannelRequest`, `ImportChatInviteRequest`, `UpdateProfileRequest`, and `SetBotCommandsRequest`; the supported `NewMessage` signature; button-family rejection; and actual client/event names. No requests were sent.

The official Telegram method pages currently display their own schema layer independently from Telethon. The pinned package's generated constructors establish the Python call shape; the method pages establish permission and protocol meaning. A listed Telegram capability does not establish that every higher-level wrapper or account supports it.

Some fetched `tl.telethon.dev` raw-reference pages returned unrelated content during this review, so they were excluded from evidence. Use the official Telegram method pages and the installed pinned distribution for the raw examples here. Stable documentation and server rules may change after the cutoff; this record makes no future support promise.

See [validation.md](validation.md) for exact offline checks and their limits.

## Focused audit — 2026-10-04

[Native callback updates](https://core.telegram.org/constructor/updateBotCallbackQuery) may omit byte data for game callbacks. The callback parser now rejects non-byte/None data without raising; the recovery regression builds an actual installed 1.45.0 game callback event and verifies the disjoint fallback acknowledgment without a network call.

The [official release feed](https://pypi.org/pypi/Telethon/json) still reports 1.45.0. The [event reference](https://docs.telethon.dev/en/stable/modules/events.html) and exact installed 1.45.0 CallbackQuery builders support the disjoint func filters used for recognized/recovery callbacks. Eight offline checks pass, including actual builder filtering of valid, stale, zero-owner and oversized data, acknowledgment without editing unknown menus, identity refusal and layer 229 constructors. Authentication guidance now keeps business handlers disabled until the restored identity is verified.
