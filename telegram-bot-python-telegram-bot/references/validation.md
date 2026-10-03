# Offline validation — 2026-10-03

The starter was checked against installed python-telegram-bot 22.8. Five tests in
[offline_check.py](../assets/starter/offline_check.py) pass without Telegram calls.
They check minute-to-second scheduling, invalid delays, sequential conversation
construction, persistent state round-trip and callback ownership. Run that file from its starter
directory with [requirements.txt](../assets/starter/requirements.txt) installed.

The repository [validation record](../../docs/VALIDATION.md) supplies the combined
runner. These checks do not authenticate a bot or establish webhook delivery,
real permissions or client rendering.
