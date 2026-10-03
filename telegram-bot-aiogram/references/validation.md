# Offline validation — 2026-10-03

The starter was checked against installed aiogram 3.31.0. Five tests in
[offline_check.py](../assets/starter/offline_check.py) pass without Telegram calls.
They exercise state validation/cancellation, escaped output, callback ownership,
callback payload limits and real dispatcher subscriptions using mocked messages.
Run that file from its
starter directory with [requirements.txt](../assets/starter/requirements.txt) installed.

The repository [validation record](../../docs/VALIDATION.md) supplies the combined
runner. Redis deployment, webhook hosting and actual Telegram reception/rendering
require separate integration checks.
