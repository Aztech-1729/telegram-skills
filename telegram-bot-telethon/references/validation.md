# Offline validation — 2026-10-03

The starter was checked against installed Telethon 1.45.0, MTProto layer 229.
Seven tests in [offline_check.py](../assets/starter/offline_check.py) pass without
connecting to Telegram. They cover credential shape, existing-session identity,
callback byte limits and ownership, acknowledgment before edit, echo/menu behavior,
actual event builders, raw-request constructors and incompatible button families.

Run that file from its starter directory with
[requirements.txt](../assets/starter/requirements.txt) installed. The repository
[validation record](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/VALIDATION.md) supplies the combined runner.
Authentication, permissions, history/media retrieval and FloodWait behavior were
not exercised against a live account.
