"""Read-only checks of public upstream documentation and package services.

These checks verify reachability and expected response shape, not every API
claim or the behavior of an authenticated Telegram bot. No credentials needed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    marker: str = ""
    json_key: str = ""


TARGETS = (
    Target("Telegram Bot API", "https://core.telegram.org/bots/api", "getMe"),
    Target("Telegram Mini Apps", "https://core.telegram.org/bots/webapps", "initData"),
    Target("Telegram Stars", "https://core.telegram.org/bots/payments-stars", "XTR"),
    Target("python-telegram-bot", "https://docs.python-telegram-bot.org/en/stable/", "Application"),
    Target("aiogram", "https://docs.aiogram.dev/en/latest/", "Dispatcher"),
    Target("Telethon", "https://docs.telethon.dev/en/stable/", "TelegramClient"),
    Target("grammY documentation source", "https://raw.githubusercontent.com/grammyjs/website/main/site/docs/guide/getting-started.md", "Bot"),
    Target("Telegraf", "https://telegraf.js.org/", "Telegraf"),
    Target("Go Telegram", "https://raw.githubusercontent.com/go-telegram/bot/main/README.md", "bot.New"),
    Target("gotd", "https://raw.githubusercontent.com/gotd/td/main/README.md", "telegram"),
    Target("TelegramBots Maven", "https://repo1.maven.org/maven2/org/telegram/telegrambots-longpolling/maven-metadata.xml", "<version>"),
    Target("Telegram.Bot NuGet", "https://api.nuget.org/v3-flatcontainer/telegram.bot/index.json", json_key="versions"),
    Target("PHP SDK", "https://telegram-bot-sdk.com/docs/", "Telegram"),
    Target("teloxide", "https://docs.rs/teloxide/latest/teloxide/", "Dispatcher"),
)
RETRYABLE = {429, 500, 502, 503, 504}
MAX_BYTES = 4 * 1024 * 1024


def retry_delay(value: str | None, attempt: int, *, now=None) -> float:
    """Honor bounded Retry-After seconds or dates; avoid unbounded CI waits."""
    fallback = min(2 ** attempt, 8)
    if not value:
        return fallback
    try:
        delay = float(value)
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            delay = (date - (now or datetime.now(timezone.utc))).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return fallback
    return max(0, min(delay, 30))


def fetch(url: str, *, opener=urlopen, sleeper=time.sleep, attempts=3) -> tuple[bytes, str]:
    request = Request(url, headers={
        "User-Agent": "telegram-skills-public-docs-check/1.0",
        "Accept": "text/html,application/json,application/xml,text/plain;q=0.9",
    })
    for attempt in range(attempts):
        try:
            with opener(request, timeout=25) as response:
                if not 200 <= response.status < 300:
                    raise ValueError(f"Unexpected HTTP status {response.status}")
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise ValueError("Response exceeds four MiB limit")
                if not content.strip():
                    raise ValueError("Empty response")
                return content, response.geturl()
        except HTTPError as error:
            if error.code not in RETRYABLE or attempt + 1 == attempts:
                raise ValueError(f"HTTP {error.code}") from None
            sleeper(retry_delay(error.headers.get("Retry-After"), attempt))
        except (URLError, TimeoutError, OSError):
            if attempt + 1 == attempts:
                raise ValueError("Network connection failed after bounded retries") from None
            sleeper(retry_delay(None, attempt))
    raise ValueError("No attempts configured")


def check(target: Target, *, fetcher=fetch) -> dict:
    result = {"name": target.name, "url": target.url}
    try:
        content, final_url = fetcher(target.url)
        if target.json_key:
            data = json.loads(content)
            if not isinstance(data, dict) or not data.get(target.json_key):
                raise ValueError(f"Missing non-empty JSON field {target.json_key}")
        elif target.marker.casefold() not in content.decode("utf-8", errors="replace").casefold():
            raise ValueError(f"Expected documentation marker missing: {target.marker}")
        result.update(status="passed", final_url=final_url, bytes=len(content))
    except (ValueError, UnicodeError) as error:
        result.update(status="failed", error=str(error))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("online-checks.json"))
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(check, TARGETS))
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "kind": "public-read-only", "results": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["### Public upstream online checks", "", "| Source | Result |", "| --- | --- |"]
    for result in results:
        print(f"{result['status'].upper()}: {result['name']}" + (f" ({result['error']})" if "error" in result else ""))
        lines.append(f"| {result['name']} | {result['status']} |")
    lines.extend(["", "These are public endpoint and response-shape checks; authenticated bot behavior is separate.", ""])
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    return int(any(result["status"] != "passed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
