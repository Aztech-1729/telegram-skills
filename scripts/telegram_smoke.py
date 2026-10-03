"""Optionally authenticate a dedicated test bot using read-only getMe only."""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a token-bearing URL to a redirect destination.


def validate_response(data: object) -> bool:
    if not isinstance(data, dict) or data.get("ok") is not True:
        return False
    bot = data.get("result")
    return (isinstance(bot, dict) and bot.get("is_bot") is True
            and type(bot.get("id")) is int and bot["id"] > 0)


def main() -> int:
    token = os.environ.get("TELEGRAM_TEST_BOT_TOKEN", "")
    if not token:
        message = "SKIPPED: Telegram getMe; TELEGRAM_TEST_BOT_TOKEN is not configured."
        code = 0
    elif not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,}", token):
        message = "FAILED: TELEGRAM_TEST_BOT_TOKEN is not a Telegram bot token."
        code = 1
    else:
        try:
            request = Request(f"https://api.telegram.org/bot{token}/getMe", headers={"User-Agent": "telegram-skills-read-only-smoke/1.0"})
            with build_opener(NoRedirect).open(request, timeout=20) as response:
                body = response.read(65537)
                if len(body) > 65536 or not validate_response(json.loads(body)):
                    raise ValueError("Unexpected getMe response")
            message, code = "PASSED: Telegram getMe authenticated the dedicated test bot (read-only).", 0
        except (HTTPError, URLError, OSError, ValueError):
            # Exception reprs and Telegram descriptions may expose credentials.
            message, code = "FAILED: Telegram getMe could not authenticate or returned an invalid response; credentials were not logged.", 1
    print(message)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(f"\n### Optional Telegram integration smoke\n\n{message}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
