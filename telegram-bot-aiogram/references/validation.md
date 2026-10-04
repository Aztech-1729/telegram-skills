# Offline validation — 2026-10-04

The starter was checked against aiogram 3.31.0 on Python 3.12 in an isolated environment with its Redis extra. Eight tests in
[offline_check.py](../assets/starter/offline_check.py) pass without Telegram calls.
They exercise state validation/cancellation, escaped output, callback ownership,
callback payload limits, real stale-callback dispatch through feed_update with a mocked
Bot session, failed-reply state retention, and Redis state/lock key separation by bot.
The Redis client is constructed and closed locally; no Redis connection is made.
Run that file from its
starter directory with [requirements.txt](../assets/starter/requirements.txt) installed.

The repository [validation record](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/VALIDATION.md) supplies the combined
runner. Redis deployment, webhook hosting and actual Telegram reception/rendering
require separate integration checks.
