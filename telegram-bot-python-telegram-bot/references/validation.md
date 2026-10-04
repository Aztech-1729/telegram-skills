# Offline validation — 2026-10-04

The starter was checked against python-telegram-bot 22.8 on Python 3.12 in an isolated environment with the advertised job-queue/rate-limiter extras. Eight tests in
[offline_check.py](../assets/starter/offline_check.py) pass without Telegram calls.
They check minute-to-second scheduling, invalid delays, sequential conversation
construction, persistent state round-trip, callback ownership/stale route selection,
failed-reply form recovery and nontext input hints. Run that file from its starter
directory with [requirements.txt](../assets/starter/requirements.txt) installed.

The repository [validation record](https://github.com/Aztech-1729/telegram-skills/blob/main/docs/VALIDATION.md) supplies the combined
runner. These checks do not authenticate a bot or establish webhook delivery,
real permissions or client rendering.
