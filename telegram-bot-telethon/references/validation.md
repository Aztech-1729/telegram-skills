# Offline validation — 2026-10-04

The starter was checked against Telethon 1.45.0, MTProto layer 229, on Python 3.12 in an isolated environment.
Eight tests in [offline_check.py](../assets/starter/offline_check.py) pass without
connecting to Telegram. They cover credential shape, existing-session identity,
callback byte limits and ownership, acknowledgment before edit, echo/menu behavior,
actual event builders, raw-request constructors, incompatible button families,
and disjoint recovery routing for malformed/oversized/stale callbacks.

Run that file from its starter directory with
[requirements.txt](../assets/starter/requirements.txt) installed. The repository
[validation record](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/VALIDATION.md) supplies the combined runner.
Authentication, permissions, history/media retrieval and FloodWait behavior were
not exercised against a live account.
